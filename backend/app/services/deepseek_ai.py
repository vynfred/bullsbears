"""
DeepSeek AI integration for sentiment analysis and social refinement.
Specialized for news sentiment, social media refinement, and narrative synthesis.
Part of the dual AI system: Grok scouts → DeepSeek refines → Consensus engine.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
import json
from dataclasses import dataclass

from ..core.config import settings
from ..core.redis_client import get_redis_client
from .cost_monitor import CostMonitor, APIService

logger = logging.getLogger(__name__)

@dataclass
class DeepSeekSentimentAnalysis:
    """Data class for DeepSeek sentiment analysis results."""
    sentiment_score: float  # -1.0 to +1.0 (bearish to bullish)
    confidence: float       # 0-100
    narrative: str         # Qualitative explanation
    key_themes: List[str]  # Main sentiment drivers
    crowd_psychology: str  # FOMO, fear, euphoria, etc.
    sarcasm_detected: bool # Whether sarcasm/memes were filtered
    social_news_bridge: float  # Correlation between social and news (-1 to +1)

@dataclass
class DeepSeekNewsAnalysis:
    """Data class for DeepSeek news sentiment analysis."""
    sentiment_score: float  # -1.0 to +1.0
    confidence: float       # 0-100
    impact_assessment: str  # HIGH, MEDIUM, LOW
    key_events: List[str]   # Main news drivers
    earnings_proximity: bool # Near earnings date
    fundamental_impact: str # Qualitative assessment

class DeepSeekAIService:
    """Service for DeepSeek AI sentiment analysis and social refinement."""
    
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.session = None
        self.redis_client = None
        self.cost_monitor = None
        
        # Cache TTL settings (5 minutes for social/news as per optimization strategy)
        self.cache_ttl_social = 300  # 5 minutes
        self.cache_ttl_news = 300    # 5 minutes
        
        if not self.api_key:
            logger.warning("DeepSeek API key not configured")
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.api_key:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            )
        self.redis_client = await get_redis_client()

        # Initialize cost monitor
        self.cost_monitor = CostMonitor()
        await self.cost_monitor.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.cost_monitor:
            await self.cost_monitor.__aexit__(exc_type, exc_val, exc_tb)
        if self.session:
            await self.session.close()
    
    async def analyze_news_sentiment(self, symbol: str, news_data: Dict[str, Any]) -> Optional[DeepSeekNewsAnalysis]:
        """
        Analyze news sentiment with DeepSeek's advanced language understanding.
        
        Args:
            symbol: Stock symbol
            news_data: Raw news data from NewsAPI/Finnhub
            
        Returns:
            DeepSeekNewsAnalysis with sentiment and impact assessment
        """
        if not self.api_key:
            logger.warning("DeepSeek API key not available")
            return None
        
        # Check cache first
        cache_key = f"deepseek_news:{symbol}:{self._get_cache_timestamp(self.cache_ttl_news)}"
        if self.redis_client:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Using cached DeepSeek news analysis for {symbol}")
                return DeepSeekNewsAnalysis(**json.loads(cached_result))
        
        try:
            prompt = self._build_news_analysis_prompt(symbol, news_data)
            
            # Keep prompt under 2k tokens for cost optimization
            if len(prompt) > 8000:  # Rough token estimation (4 chars per token)
                prompt = prompt[:8000] + "...\n\nAnalyze the above news data for sentiment."
            
            response = await self._call_deepseek_api(prompt)
            if response:
                analysis = self._parse_news_analysis_response(response)
                
                # Cache the result
                if self.redis_client and analysis:
                    await self.redis_client.set(
                        cache_key,
                        json.dumps(analysis.__dict__),
                        expire=self.cache_ttl_news
                    )
                
                return analysis
                
        except Exception as e:
            logger.error(f"Error in DeepSeek news analysis: {e}")
            return None
    
    async def refine_social_sentiment(self, symbol: str, grok_social_packet: Dict[str, Any]) -> Optional[DeepSeekSentimentAnalysis]:
        """
        Refine Grok's social sentiment data with advanced sarcasm detection and crowd psychology.
        
        Args:
            symbol: Stock symbol
            grok_social_packet: Structured data packet from Grok's social scouting
            
        Returns:
            DeepSeekSentimentAnalysis with refined sentiment and psychological insights
        """
        if not self.api_key:
            logger.warning("DeepSeek API key not available")
            return None
        
        # Check cache first
        cache_key = f"deepseek_social:{symbol}:{self._get_cache_timestamp(self.cache_ttl_social)}"
        if self.redis_client:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Using cached DeepSeek social analysis for {symbol}")
                return DeepSeekSentimentAnalysis(**json.loads(cached_result))
        
        try:
            prompt = self._build_social_refinement_prompt(symbol, grok_social_packet)
            
            # Keep prompt under 2k tokens for cost optimization
            if len(prompt) > 8000:  # Rough token estimation
                prompt = prompt[:8000] + "...\n\nRefine the above social sentiment analysis."
            
            response = await self._call_deepseek_api(prompt)
            if response:
                analysis = self._parse_social_analysis_response(response)
                
                # Cache the result
                if self.redis_client and analysis:
                    await self.redis_client.set(
                        cache_key,
                        json.dumps(analysis.__dict__),
                        expire=self.cache_ttl_social
                    )
                
                return analysis
                
        except Exception as e:
            logger.error(f"Error in DeepSeek social refinement: {e}")
            return None
    
    async def synthesize_narrative(self, symbol: str, news_analysis: DeepSeekNewsAnalysis, 
                                 social_analysis: DeepSeekSentimentAnalysis) -> str:
        """
        Synthesize a coherent narrative from news and social sentiment analysis.
        
        Args:
            symbol: Stock symbol
            news_analysis: News sentiment analysis results
            social_analysis: Social sentiment analysis results
            
        Returns:
            Synthesized narrative string
        """
        try:
            prompt = f"""
Synthesize a coherent market narrative for {symbol} based on:

NEWS SENTIMENT: {news_analysis.sentiment_score:.2f} ({news_analysis.impact_assessment} impact)
Key Events: {', '.join(news_analysis.key_events)}

SOCIAL SENTIMENT: {social_analysis.sentiment_score:.2f} (Confidence: {social_analysis.confidence:.1f}%)
Crowd Psychology: {social_analysis.crowd_psychology}
Key Themes: {', '.join(social_analysis.key_themes)}

Create a 2-3 sentence narrative explaining the overall market sentiment and key drivers.
Focus on actionable insights for options traders.
"""
            
            response = await self._call_deepseek_api(prompt)
            return response.get('content', 'Unable to synthesize narrative') if response else 'API unavailable'
            
        except Exception as e:
            logger.error(f"Error synthesizing narrative: {e}")
            return f"Error synthesizing narrative for {symbol}"
    
    def _get_cache_timestamp(self, ttl_seconds: int) -> str:
        """Get cache timestamp rounded to TTL intervals for consistent caching."""
        import time
        current_time = int(time.time())
        rounded_time = (current_time // ttl_seconds) * ttl_seconds
        return str(rounded_time)
    
    async def _call_deepseek_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Make API call to DeepSeek with error handling and retries."""
        if not self.session:
            logger.error("DeepSeek session not initialized")
            return None
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a financial sentiment analysis expert specializing in social media and news analysis for options trading."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        try:
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    data = await response.json()

                    # Track API usage and cost
                    if self.cost_monitor:
                        tokens_used = data.get('usage', {}).get('total_tokens', 0)
                        await self.cost_monitor.track_api_call(
                            service=APIService.DEEPSEEK,
                            tokens_used=tokens_used
                        )

                    return {
                        'content': data['choices'][0]['message']['content'],
                        'usage': data.get('usage', {})
                    }
                else:
                    logger.error(f"DeepSeek API error: {response.status}")

                    # Track failed API call
                    if self.cost_monitor:
                        await self.cost_monitor.track_api_call(
                            service=APIService.DEEPSEEK,
                            tokens_used=0  # No tokens used on failure
                        )

                    return None
                    
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return None

    def _build_news_analysis_prompt(self, symbol: str, news_data: Dict[str, Any]) -> str:
        """Build prompt for news sentiment analysis."""
        headlines = news_data.get('headlines', [])
        recent_news = headlines[:10] if headlines else []  # Limit to recent news

        prompt = f"""
Analyze the news sentiment for {symbol} and provide structured analysis:

RECENT NEWS HEADLINES:
{chr(10).join([f"- {item.get('title', 'No title')}" for item in recent_news])}

EARNINGS DATA:
{news_data.get('earnings', 'No earnings data available')}

Provide analysis in this exact format:
SENTIMENT_SCORE: [number from -1.0 to +1.0]
CONFIDENCE: [number from 0 to 100]
IMPACT_ASSESSMENT: [HIGH/MEDIUM/LOW]
KEY_EVENTS: [comma-separated list of main drivers]
EARNINGS_PROXIMITY: [true/false]
FUNDAMENTAL_IMPACT: [brief qualitative assessment]

Focus on quantifiable sentiment and avoid speculation.
"""
        return prompt

    def _build_social_refinement_prompt(self, symbol: str, grok_social_packet: Dict[str, Any]) -> str:
        """Build prompt for social sentiment refinement."""
        prompt = f"""
Refine the social sentiment analysis for {symbol} using advanced psychological insights:

GROK'S SOCIAL DATA PACKET:
Raw Sentiment: {grok_social_packet.get('raw_sentiment', 'N/A')}
Mention Count: {grok_social_packet.get('mention_count', 0)}
Key Themes: {grok_social_packet.get('themes', [])}
Source Breakdown: {grok_social_packet.get('sources', {})}

REFINEMENT TASKS:
1. Detect sarcasm, memes, and ironic content
2. Analyze crowd psychology (FOMO, fear, euphoria, capitulation)
3. Identify narrative threads and momentum
4. Assess social-news correlation

Provide analysis in this exact format:
SENTIMENT_SCORE: [refined number from -1.0 to +1.0]
CONFIDENCE: [number from 0 to 100]
NARRATIVE: [2-3 sentence explanation]
KEY_THEMES: [comma-separated refined themes]
CROWD_PSYCHOLOGY: [dominant psychological state]
SARCASM_DETECTED: [true/false]
SOCIAL_NEWS_BRIDGE: [correlation score from -1.0 to +1.0]

Focus on psychological nuances and filter out noise.
"""
        return prompt

    def _parse_news_analysis_response(self, response: Dict[str, Any]) -> Optional[DeepSeekNewsAnalysis]:
        """Parse DeepSeek news analysis response."""
        try:
            content = response.get('content', '')

            # Extract structured data from response
            sentiment_score = self._extract_float_value(content, 'SENTIMENT_SCORE:', -1.0, 1.0)
            confidence = self._extract_float_value(content, 'CONFIDENCE:', 0, 100)
            impact_assessment = self._extract_string_value(content, 'IMPACT_ASSESSMENT:', ['HIGH', 'MEDIUM', 'LOW'])
            key_events = self._extract_list_value(content, 'KEY_EVENTS:')
            earnings_proximity = self._extract_bool_value(content, 'EARNINGS_PROXIMITY:')
            fundamental_impact = self._extract_string_value(content, 'FUNDAMENTAL_IMPACT:')

            return DeepSeekNewsAnalysis(
                sentiment_score=sentiment_score,
                confidence=confidence,
                impact_assessment=impact_assessment,
                key_events=key_events,
                earnings_proximity=earnings_proximity,
                fundamental_impact=fundamental_impact
            )

        except Exception as e:
            logger.error(f"Error parsing news analysis response: {e}")
            return None

    def _parse_social_analysis_response(self, response: Dict[str, Any]) -> Optional[DeepSeekSentimentAnalysis]:
        """Parse DeepSeek social sentiment analysis response."""
        try:
            content = response.get('content', '')

            # Extract structured data from response
            sentiment_score = self._extract_float_value(content, 'SENTIMENT_SCORE:', -1.0, 1.0)
            confidence = self._extract_float_value(content, 'CONFIDENCE:', 0, 100)
            narrative = self._extract_string_value(content, 'NARRATIVE:')
            key_themes = self._extract_list_value(content, 'KEY_THEMES:')
            crowd_psychology = self._extract_string_value(content, 'CROWD_PSYCHOLOGY:')
            sarcasm_detected = self._extract_bool_value(content, 'SARCASM_DETECTED:')
            social_news_bridge = self._extract_float_value(content, 'SOCIAL_NEWS_BRIDGE:', -1.0, 1.0)

            return DeepSeekSentimentAnalysis(
                sentiment_score=sentiment_score,
                confidence=confidence,
                narrative=narrative,
                key_themes=key_themes,
                crowd_psychology=crowd_psychology,
                sarcasm_detected=sarcasm_detected,
                social_news_bridge=social_news_bridge
            )

        except Exception as e:
            logger.error(f"Error parsing social analysis response: {e}")
            return None

    def _extract_float_value(self, content: str, key: str, min_val: float = None, max_val: float = None) -> float:
        """Extract float value from structured response."""
        try:
            lines = content.split('\n')
            for line in lines:
                if key in line:
                    value_str = line.split(key)[1].strip()
                    value = float(value_str.split()[0])  # Take first number
                    if min_val is not None and value < min_val:
                        value = min_val
                    if max_val is not None and value > max_val:
                        value = max_val
                    return value
            return 0.0  # Default value
        except:
            return 0.0

    def _extract_string_value(self, content: str, key: str, valid_options: List[str] = None) -> str:
        """Extract string value from structured response."""
        try:
            lines = content.split('\n')
            for line in lines:
                if key in line:
                    value = line.split(key)[1].strip()
                    if valid_options and value not in valid_options:
                        return valid_options[0]  # Default to first option
                    return value
            return ""
        except:
            return ""

    def _extract_list_value(self, content: str, key: str) -> List[str]:
        """Extract list value from structured response."""
        try:
            lines = content.split('\n')
            for line in lines:
                if key in line:
                    value_str = line.split(key)[1].strip()
                    return [item.strip() for item in value_str.split(',') if item.strip()]
            return []
        except:
            return []

    def _extract_bool_value(self, content: str, key: str) -> bool:
        """Extract boolean value from structured response."""
        try:
            lines = content.split('\n')
            for line in lines:
                if key in line:
                    value_str = line.split(key)[1].strip().lower()
                    return value_str in ['true', 'yes', '1']
            return False
        except:
            return False
