#!/usr/bin/env python3
"""
AI Feature Extraction
Creates structured JSON output prompts for Grok and DeepSeek to extract features for ensemble training.
Integrates Grok/DeepSeek outputs as features in the ensemble models.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Import actual AI services
from ..services.grok_ai import GrokAIService
from ..services.deepseek_ai import DeepSeekAIService
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class AIFeatureExtractor:
    """Extract structured AI features from Grok and DeepSeek for ensemble training."""

    def __init__(self):
        self.grok_service = GrokAIService()
        self.deepseek_service = DeepSeekAIService()
        self.redis_client = None

        # Cache TTL settings (1 hour for AI features as per spec)
        self.cache_ttl_ai = 3600  # 1 hour
        
    async def extract_grok_features(self, ticker: str, data: pd.DataFrame, 
                                  technical_summary: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract structured technical analysis features from Grok.
        
        Returns structured JSON with specific numeric features:
        - technical_confidence: 0.0-1.0 (overall technical setup strength)
        - volume_surge_detected: 0.0/1.0 (binary: unusual volume detected)
        - rsi_oversold: 0.0-1.0 (RSI oversold strength, 0=not oversold, 1=extremely oversold)
        - social_buzz_score: 0.0-1.0 (social media activity level)
        """
        try:
            # Prepare technical context for Grok
            latest_data = data.iloc[-1]
            rsi_14 = technical_summary.get('rsi_14', 50.0)
            volume_ratio = technical_summary.get('volume_ratio', 1.0)
            macd_signal = technical_summary.get('macd_signal', 0.0)
            bb_position = technical_summary.get('bb_position', 0.5)
            
            # Create structured prompt for Grok
            grok_prompt = f"""
Analyze {ticker} technical setup and return ONLY a JSON object with these exact fields:

TECHNICAL DATA:
- Current Price: ${latest_data['close']:.2f}
- RSI(14): {rsi_14:.1f}
- Volume Ratio: {volume_ratio:.2f}x average
- MACD Signal: {macd_signal:.3f}
- Bollinger Position: {bb_position:.2f} (0=bottom, 1=top)
- 5-day price change: {((latest_data['close'] / data.iloc[-min(6, len(data))]['close']) - 1) * 100 if len(data) >= 2 else 0.0:.1f}%

REQUIRED JSON OUTPUT FORMAT:
{{
    "technical_confidence": 0.85,
    "volume_surge_detected": 1.0,
    "rsi_oversold": 0.75,
    "social_buzz_score": 0.60
}}

SCORING RULES:
- technical_confidence: 0.0-1.0 (combine RSI, MACD, volume, momentum for moon/rug potential)
- volume_surge_detected: 1.0 if volume >1.5x average, 0.0 otherwise
- rsi_oversold: 0.0 if RSI>50, scale 0.0-1.0 for RSI 50→20 (lower RSI = higher score)
- social_buzz_score: 0.0-1.0 estimate based on ticker popularity and recent price action

Return ONLY the JSON object, no explanation.
"""
            
            # Get Grok analysis using the actual API
            grok_analysis = await self.grok_service.analyze_option_play(
                symbol=ticker,
                technical_data=technical_summary,
                news_data={},
                social_data={},
                polymarket_data=[],
                catalyst_data={},
                unusual_volume_data={},
                options_flow_data={},
                confidence_score=0.5
            )
            
            # Parse Grok analysis response
            if grok_analysis:
                grok_features = self._parse_grok_analysis(grok_analysis, ticker)
            else:
                logger.warning(f"⚠️ Grok analysis failed for {ticker}, using defaults")
                grok_features = self._get_default_grok_features()

            logger.info(f"✅ Grok features for {ticker}: {grok_features}")
            return grok_features
            
        except Exception as e:
            logger.error(f"❌ Grok feature extraction failed for {ticker}: {e}")
            return self._get_default_grok_features()
    
    async def extract_deepseek_features(self, ticker: str, data: pd.DataFrame,
                                      news_context: Optional[str] = None) -> Dict[str, float]:
        """
        Extract structured sentiment analysis features from DeepSeek.
        
        Returns structured JSON with specific numeric features:
        - sentiment_score: 0.0-1.0 (overall market sentiment, 0=bearish, 1=bullish)
        - news_sentiment: 0.0-1.0 (recent news sentiment)
        - narrative_strength: 0.0-1.0 (strength of bullish/bearish narrative)
        - bearish_keywords: 0-10 (count of bearish keywords in recent content)
        """
        try:
            # Prepare market context for DeepSeek (with safe indexing)
            latest_data = data.iloc[-1]

            # Safe price change calculations
            if len(data) >= 2:
                price_change_1d = ((latest_data['close'] / data.iloc[-2]['close']) - 1) * 100
            else:
                price_change_1d = 0.0

            if len(data) >= 6:
                price_change_5d = ((latest_data['close'] / data.iloc[-6]['close']) - 1) * 100
            else:
                price_change_5d = 0.0
            
            # Create structured prompt for DeepSeek
            deepseek_prompt = f"""
Analyze sentiment for {ticker} and return ONLY a JSON object with these exact fields:

MARKET CONTEXT:
- Ticker: {ticker}
- Current Price: ${latest_data['close']:.2f}
- 1-day change: {price_change_1d:.1f}%
- 5-day change: {price_change_5d:.1f}%
- Recent news: {news_context or 'No specific news provided'}

REQUIRED JSON OUTPUT FORMAT:
{{
    "sentiment_score": 0.65,
    "news_sentiment": 0.70,
    "narrative_strength": 0.80,
    "bearish_keywords": 2
}}

SCORING RULES:
- sentiment_score: 0.0-1.0 (overall market sentiment: 0=very bearish, 0.5=neutral, 1=very bullish)
- news_sentiment: 0.0-1.0 (recent news tone: 0=negative news, 1=positive news)
- narrative_strength: 0.0-1.0 (how strong is the current narrative: 0=weak/mixed, 1=very strong)
- bearish_keywords: 0-10 integer count (crash, dump, rug, sell-off, bearish, etc.)

Consider:
- Recent price action momentum
- Typical market sentiment for this ticker
- News tone and narrative consistency
- Social media sentiment proxies

Return ONLY the JSON object, no explanation.
"""
            
            # Get DeepSeek analysis using the actual API
            deepseek_analysis = await self.deepseek_service.analyze_news_sentiment(
                symbol=ticker,
                news_data={'context': news_context or 'No recent news available'}
            )

            # Parse DeepSeek analysis response
            if deepseek_analysis:
                deepseek_features = self._parse_deepseek_analysis(deepseek_analysis, ticker)
            else:
                logger.warning(f"⚠️ DeepSeek analysis failed for {ticker}, using defaults")
                deepseek_features = self._get_default_deepseek_features()
            
            logger.info(f"✅ DeepSeek features for {ticker}: {deepseek_features}")
            return deepseek_features
            
        except Exception as e:
            logger.error(f"❌ DeepSeek feature extraction failed for {ticker}: {e}")
            return self._get_default_deepseek_features()
    
    async def extract_all_ai_features(self, ticker: str, data: pd.DataFrame,
                                    technical_summary: Dict[str, Any],
                                    news_context: Optional[str] = None) -> Dict[str, float]:
        """Extract both Grok and DeepSeek features concurrently with Redis caching."""
        try:
            # Initialize Redis client if needed
            if not self.redis_client:
                try:
                    self.redis_client = await get_redis_client()
                except Exception as e:
                    logger.warning(f"⚠️ Redis unavailable: {e} (continuing without cache)")
                    self.redis_client = None

            # Create cache key
            cache_key = f"ai_features:{ticker}:{datetime.now().strftime('%Y-%m-%d')}"

            # 1. Try cache first
            if self.redis_client:
                try:
                    cached_features = await self.redis_client.get(cache_key)
                    if cached_features:
                        logger.info(f"🎯 Using cached AI features for {ticker}")
                        return cached_features
                except Exception as e:
                    logger.warning(f"⚠️ Cache read failed: {e}")

            logger.info(f"🤖 Extracting AI features for {ticker}...")

            # 2. Run both AI services concurrently for speed
            grok_task = self.extract_grok_features(ticker, data, technical_summary)
            deepseek_task = self.extract_deepseek_features(ticker, data, news_context)

            grok_features, deepseek_features = await asyncio.gather(
                grok_task, deepseek_task, return_exceptions=True
            )

            # Handle any exceptions
            if isinstance(grok_features, Exception):
                logger.error(f"❌ Grok extraction failed: {grok_features}")
                grok_features = self._get_default_grok_features()

            if isinstance(deepseek_features, Exception):
                logger.error(f"❌ DeepSeek extraction failed: {deepseek_features}")
                deepseek_features = self._get_default_deepseek_features()

            # Combine all AI features
            ai_features = {
                # Grok features (technical + social)
                'ai_technical_confidence': grok_features['technical_confidence'],
                'ai_volume_surge_detected': grok_features['volume_surge_detected'],
                'ai_rsi_oversold': grok_features['rsi_oversold'],
                'ai_social_buzz_score': grok_features['social_buzz_score'],

                # DeepSeek features (sentiment + narrative)
                'ai_sentiment_score': deepseek_features['sentiment_score'],
                'ai_news_sentiment': deepseek_features['news_sentiment'],
                'ai_narrative_strength': deepseek_features['narrative_strength'],
                'ai_bearish_keywords': deepseek_features['bearish_keywords']
            }

            # 3. Cache the results (1 hour TTL)
            if self.redis_client:
                try:
                    await self.redis_client.setex(cache_key, self.cache_ttl_ai, json.dumps(ai_features))
                    logger.info(f"💾 Cached AI features for {ticker} (1hr TTL)")
                except Exception as e:
                    logger.warning(f"⚠️ Cache write failed: {e}")

            logger.info(f"✅ Combined AI features for {ticker}: {len(ai_features)} features")
            return ai_features

        except Exception as e:
            logger.error(f"❌ AI feature extraction failed for {ticker}: {e}")
            logger.warning(f"🔄 Falling back to RandomForest-only for {ticker}")
            return self._get_default_ai_features()
    
    def _parse_grok_analysis(self, analysis, ticker: str) -> Dict[str, float]:
        """Parse GrokAnalysis object into structured features."""
        try:
            if hasattr(analysis, 'technical_confidence'):
                return {
                    'technical_confidence': float(analysis.technical_confidence or 0.5),
                    'volume_surge_detected': float(analysis.volume_surge_detected or 0.0),
                    'rsi_oversold': float(analysis.rsi_oversold or 0.0),
                    'social_buzz_score': float(analysis.social_buzz_score or 0.5)
                }
            else:
                logger.warning(f"⚠️ Unexpected Grok analysis format for {ticker}")
                return self._get_default_grok_features()
        except Exception as e:
            logger.error(f"❌ Error parsing Grok analysis for {ticker}: {e}")
            return self._get_default_grok_features()

    def _parse_deepseek_analysis(self, analysis, ticker: str) -> Dict[str, float]:
        """Parse DeepSeekNewsAnalysis object into structured features."""
        try:
            if hasattr(analysis, 'sentiment_score'):
                return {
                    'sentiment_score': float(analysis.sentiment_score or 0.5),
                    'news_sentiment': float(analysis.news_sentiment or 0.5),
                    'narrative_strength': float(analysis.narrative_strength or 0.5),
                    'bearish_keywords': float(analysis.bearish_keywords or 0.0)
                }
            else:
                logger.warning(f"⚠️ Unexpected DeepSeek analysis format for {ticker}")
                return self._get_default_deepseek_features()
        except Exception as e:
            logger.error(f"❌ Error parsing DeepSeek analysis for {ticker}: {e}")
            return self._get_default_deepseek_features()

    def _parse_grok_response(self, response: str, ticker: str) -> Dict[str, float]:
        """Parse Grok JSON response with fallback handling."""
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # Validate and clean the response
                return {
                    'technical_confidence': float(np.clip(parsed.get('technical_confidence', 0.5), 0.0, 1.0)),
                    'volume_surge_detected': float(np.clip(parsed.get('volume_surge_detected', 0.0), 0.0, 1.0)),
                    'rsi_oversold': float(np.clip(parsed.get('rsi_oversold', 0.0), 0.0, 1.0)),
                    'social_buzz_score': float(np.clip(parsed.get('social_buzz_score', 0.5), 0.0, 1.0))
                }
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse Grok response for {ticker}: {e}")
            return self._get_default_grok_features()
    
    def _parse_deepseek_response(self, response: str, ticker: str) -> Dict[str, float]:
        """Parse DeepSeek JSON response with fallback handling."""
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # Validate and clean the response
                return {
                    'sentiment_score': float(np.clip(parsed.get('sentiment_score', 0.5), 0.0, 1.0)),
                    'news_sentiment': float(np.clip(parsed.get('news_sentiment', 0.5), 0.0, 1.0)),
                    'narrative_strength': float(np.clip(parsed.get('narrative_strength', 0.5), 0.0, 1.0)),
                    'bearish_keywords': int(np.clip(parsed.get('bearish_keywords', 0), 0, 10))
                }
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse DeepSeek response for {ticker}: {e}")
            return self._get_default_deepseek_features()
    
    def _get_default_grok_features(self) -> Dict[str, float]:
        """Default Grok features when API fails."""
        return {
            'technical_confidence': 0.5,
            'volume_surge_detected': 0.0,
            'rsi_oversold': 0.0,
            'social_buzz_score': 0.5
        }
    
    def _get_default_deepseek_features(self) -> Dict[str, float]:
        """Default DeepSeek features when API fails."""
        return {
            'sentiment_score': 0.5,
            'news_sentiment': 0.5,
            'narrative_strength': 0.5,
            'bearish_keywords': 0
        }
    
    def _get_default_ai_features(self) -> Dict[str, float]:
        """Default combined AI features when both APIs fail."""
        return {
            'ai_technical_confidence': 0.5,
            'ai_volume_surge_detected': 0.0,
            'ai_rsi_oversold': 0.0,
            'ai_social_buzz_score': 0.5,
            'ai_sentiment_score': 0.5,
            'ai_news_sentiment': 0.5,
            'ai_narrative_strength': 0.5,
            'ai_bearish_keywords': 0
        }
