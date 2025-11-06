"""
Bullish Analyzer - Identifies patterns for potential +20% stock jumps
Reuses existing stock analyzer logic with bullish-specific scoring weights
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.confidence import ConfidenceScorer
from ..services.ai_consensus import AIConsensusEngine
from ..services.model_loader import predict_bullish_ml, get_model_loader
from ..services.relative_confidence import get_relative_confidence_scorer
from ..services.short_squeeze_detector import get_short_squeeze_detector
from ..services.ai_reasoning_generator import get_ai_reasoning_generator
from ..services.enhanced_economic_events_analyzer import EnhancedEconomicEventsAnalyzer
from ..services.insider_trading_analyzer import get_insider_trading_analyzer
from ..core.redis_client import get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BullishAlert:
    """Enhanced alert for potential bullish (>20% jump) opportunity"""
    symbol: str
    company_name: str
    confidence: float  # Relative display score (50-100)
    reasons: List[str]  # AI-generated bullet-point explanations
    technical_score: float
    sentiment_score: float
    social_score: float
    earnings_score: float
    timestamp: datetime
    target_timeframe: str  # "1-3 days"
    risk_factors: List[str]

    # Enhanced ML fields
    ml_confidence: float
    ml_model_version: str
    top_features: List[Dict[str, Any]]
    prediction_method: str  # "ML" or "rule-based"

    # Relative confidence fields
    confidence_level: str  # "HIGH", "MEDIUM", "SPECULATIVE"
    confidence_emoji: str  # "🔥", "📈", "⚡"
    confidence_description: str  # User-friendly description
    raw_confidence: float  # Original ML score (0-1)
    percentile_rank: float  # Percentile rank (0-100)

    # Enhanced analysis fields
    economic_impact: Optional[Dict[str, Any]] = None  # Economic events analysis
    insider_analysis: Optional[Dict[str, Any]] = None  # Insider trading analysis
    squeeze_potential: Optional[Dict[str, Any]] = None  # Short squeeze analysis
    target_range: str = ""  # Enhanced target range with rationale
    estimated_days: int = 3  # Enhanced timeframe estimation


class BullishAnalyzer:
    """
    Analyzer for identifying "When Bullish?" patterns.
    Focuses on oversold technicals, positive sentiment, and volume surges.
    """
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.confidence_scorer = ConfidenceScorer()
        self.ai_consensus = AIConsensusEngine()
        self.redis_client = None
        self.use_ml_model = True  # Primary method: ML model
        self.use_relative_confidence = True  # Use relative confidence scoring

        # Enhanced data services
        self.enhanced_economic_analyzer = EnhancedEconomicEventsAnalyzer()
        
        # Bullish-specific scoring weights (total = 100%)
        self.weights = {
            "technical": 40.0,    # Technical indicators (RSI, MACD, volume)
            "sentiment": 30.0,    # News and social sentiment
            "earnings": 20.0,     # Earnings expectations and calendar
            "social": 10.0        # CEO activity, social mentions
        }

        # Enhanced bullish pattern thresholds
        self.confidence_threshold = 70.0  # Legacy threshold (not used with relative confidence)
        self.ml_confidence_threshold = 48.0  # >48% for more picks (user requested)
        self.rsi_oversold_threshold = 30.0
        self.volume_surge_threshold = 1.5  # 1.5x average volume
        self.positive_sentiment_threshold = 0.3
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.redis_client = await get_redis_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.redis_client:
            await self.redis_client.disconnect()

    async def analyze_bullish_potential(self, symbol: str, company_name: str = None) -> Optional[BullishAlert]:
        """
        Analyze a symbol for bullish potential using enhanced ML model with relative confidence,
        economic events, insider trading, and short squeeze detection.

        Args:
            symbol: Stock symbol to analyze
            company_name: Company name (optional)

        Returns:
            BullishAlert if confidence > relative threshold, None otherwise
        """
        try:
            logger.info(f"🔍 Analyzing bullish potential for {symbol}")

            # Use existing confidence scorer for comprehensive analysis
            analysis_result = await self.confidence_scorer.analyze_stock(
                symbol, None, company_name or symbol
            )

            if not analysis_result:
                logger.warning(f"No analysis result for {symbol}")
                return None

            # Extract components for analysis
            technical_data = analysis_result.get('technical_analysis', {})
            news_data = analysis_result.get('news_analysis', {})
            social_data = analysis_result.get('social_analysis', {})

            # Try ML prediction first
            if self.use_ml_model:
                ml_result = await self._predict_with_ml_model(technical_data, news_data, social_data)
                if ml_result:
                    ml_confidence, ml_details, features = ml_result

                    # Use relative confidence scoring instead of fixed threshold
                    if self.use_relative_confidence:
                        return await self._create_enhanced_ml_alert(
                            symbol, company_name, ml_confidence, ml_details, features,
                            technical_data, news_data, social_data
                        )
                    # Fallback to old threshold system
                    elif ml_confidence >= self.ml_confidence_threshold:
                        return await self._create_ml_alert(
                            symbol, company_name, ml_confidence, ml_details, features,
                            technical_data, news_data
                        )
                    else:
                        logger.info(f"🚀 {symbol}: ML confidence {ml_confidence:.1%} below threshold")

            # Fallback to rule-based analysis
            logger.info(f"🔄 {symbol}: Using rule-based fallback analysis")
            return await self._analyze_with_rules(symbol, company_name, technical_data, news_data, social_data)
                
        except Exception as e:
            logger.error(f"Error analyzing bullish potential for {symbol}: {e}")
            return None

    async def _predict_with_ml_model(self, technical_data: Dict, news_data: Dict, social_data: Dict) -> Optional[Tuple[float, Dict, Dict]]:
        """
        Use trained ML model to predict moon potential.

        Returns:
            Tuple of (confidence, ml_details, features) or None if prediction fails
        """
        try:
            # Extract features for ML model (same as training pipeline)
            features = self._extract_ml_features(technical_data, news_data, social_data)

            if not features:
                logger.warning("Failed to extract features for ML prediction")
                return None

            # Get ML prediction
            ml_confidence, ml_details = await predict_bullish_ml(features)

            logger.info(f"🤖 ML prediction: {ml_confidence:.1%} confidence")

            return ml_confidence, ml_details, features

        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return None

    def _extract_ml_features(self, technical_data: Dict, news_data: Dict, social_data: Dict) -> Optional[Dict[str, float]]:
        """
        Extract features for ML model prediction.
        Uses same feature extraction logic as training pipeline.
        """
        try:
            features = {}

            # Basic OHLCV features (if available)
            if 'current_price' in technical_data:
                features['close'] = float(technical_data['current_price'])
            if 'open_price' in technical_data:
                features['open'] = float(technical_data['open_price'])
            if 'high_price' in technical_data:
                features['high'] = float(technical_data['high_price'])
            if 'low_price' in technical_data:
                features['low'] = float(technical_data['low_price'])
            if 'volume' in technical_data:
                features['volume'] = float(technical_data['volume'])

            # Technical indicators
            if 'rsi' in technical_data:
                features['rsi_14'] = float(technical_data['rsi'])
            if 'macd' in technical_data:
                macd_data = technical_data['macd']
                if isinstance(macd_data, dict):
                    features['macd'] = float(macd_data.get('macd', 0))
                    features['macd_signal'] = float(macd_data.get('signal', 0))
                    features['macd_histogram'] = float(macd_data.get('histogram', 0))

            # Bollinger Bands
            if 'bollinger_bands' in technical_data:
                bb_data = technical_data['bollinger_bands']
                if isinstance(bb_data, dict):
                    features['bb_upper'] = float(bb_data.get('upper', 0))
                    features['bb_middle'] = float(bb_data.get('middle', 0))
                    features['bb_lower'] = float(bb_data.get('lower', 0))

                    # Calculate BB position
                    if all(k in bb_data for k in ['upper', 'lower']) and 'current_price' in technical_data:
                        price = float(technical_data['current_price'])
                        upper = float(bb_data['upper'])
                        lower = float(bb_data['lower'])
                        if upper != lower:
                            features['bb_position'] = (price - lower) / (upper - lower)

            # Moving averages
            if 'sma_20' in technical_data:
                features['sma_20'] = float(technical_data['sma_20'])
            if 'sma_50' in technical_data:
                features['sma_50'] = float(technical_data['sma_50'])

            # Volume ratios
            if 'volume_ratio' in technical_data:
                features['volume_ratio'] = float(technical_data['volume_ratio'])

            # Price ratios
            if 'close' in features and 'open' in features and features['open'] != 0:
                features['close_open_ratio'] = features['close'] / features['open']
            if 'high' in features and 'low' in features and features['low'] != 0:
                features['high_low_ratio'] = features['high'] / features['low']

            # Sentiment features
            if 'sentiment_score' in news_data:
                features['news_sentiment'] = float(news_data['sentiment_score'])
            if 'sentiment_score' in social_data:
                features['social_sentiment'] = float(social_data['sentiment_score'])

            # Fill missing features with defaults (all 38 features from training)
            default_features = {
                # Basic OHLCV
                'close': 100.0, 'open': 100.0, 'high': 100.0, 'low': 100.0, 'volume': 1000000,
                # Price ratios
                'high_low_ratio': 1.02, 'close_open_ratio': 1.0,
                # Moving averages
                'sma_5': 100.0, 'sma_10': 100.0, 'sma_20': 100.0,
                # SMA ratios
                'close_sma5_ratio': 1.0, 'close_sma10_ratio': 1.0, 'close_sma20_ratio': 1.0,
                # RSI
                'rsi_14': 50.0, 'rsi_7': 50.0,
                # MACD
                'macd': 0.0, 'macd_signal': 0.0, 'macd_histogram': 0.0,
                # Bollinger Bands
                'bb_upper': 105.0, 'bb_middle': 100.0, 'bb_lower': 95.0, 'bb_position': 0.5,
                # Volume
                'volume_sma_10': 1000000, 'volume_ratio': 1.0,
                # Volatility and momentum
                'atr_14': 2.0, 'volatility_10': 0.02, 'momentum_5': 0.0, 'momentum_10': 0.0,
                # Rate of change
                'roc_5': 0.0, 'roc_10': 0.0,
                # Stochastic
                'stoch_k': 50.0, 'stoch_d': 50.0,
                # Other indicators
                'williams_r': -50.0, 'cci': 0.0,
                # Trend features
                'price_trend_pct': 0.0, 'volume_trend': 0.0, 'recent_volatility': 0.02, 'gap_pct': 0.0
            }

            for key, default_value in default_features.items():
                if key not in features:
                    features[key] = default_value

            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    async def _create_enhanced_ml_alert(self, symbol: str, company_name: str, ml_confidence: float,
                                      ml_details: Dict, features: Dict, technical_data: Dict,
                                      news_data: Dict, social_data: Dict) -> Optional[BullishAlert]:
        """Create enhanced bullish alert with relative confidence and advanced analysis."""
        try:
            # Get relative confidence scoring
            relative_scorer = await get_relative_confidence_scorer()
            raw_confidence = ml_confidence / 100.0  # Convert to 0-1 scale

            # Check if should generate alert using relative threshold
            should_alert = await relative_scorer.should_generate_alert(raw_confidence, "bullish")
            if not should_alert:
                logger.info(f"🚀 {symbol}: Confidence {ml_confidence:.1f}% below relative threshold")
                return None

            # Get relative confidence display
            relative_conf = await relative_scorer.get_relative_confidence(raw_confidence, "bullish")

            # Enhanced analysis - Economic events
            economic_analysis = await self.enhanced_economic_analyzer.analyze_stock_economic_impact(symbol)

            # Enhanced analysis - Insider trading
            insider_analyzer = await get_insider_trading_analyzer()
            insider_analysis = await insider_analyzer.analyze_insider_activity(symbol, 90)  # Last 90 days

            # Enhanced analysis - Short squeeze detection
            squeeze_detector = get_short_squeeze_detector()
            squeeze_signal = await squeeze_detector.detect_squeeze_potential(
                symbol, technical_data, social_data
            )

            # Generate enhanced reasoning
            reasoning_generator = get_ai_reasoning_generator()
            reasoning = reasoning_generator.generate_bullish_reasoning(
                symbol, features, ml_details, squeeze_signal
            )

            # Calculate enhanced target range
            target_range = self._calculate_enhanced_target_range(
                technical_data, relative_conf, economic_analysis, insider_analysis
            )

            # Calculate enhanced timeframe
            estimated_days = self._calculate_enhanced_timeframe(
                features, relative_conf, economic_analysis
            )

            # Format reasoning for display
            formatted_reasons = reasoning_generator.format_for_display(reasoning)

            # Create enhanced bullish alert
            alert = BullishAlert(
                symbol=symbol,
                company_name=company_name or symbol,
                confidence=relative_conf.display_score,
                reasons=formatted_reasons,
                technical_score=self._calculate_technical_score(technical_data),
                sentiment_score=float(news_data.get('sentiment_score', 0.5)) * 100,
                social_score=float(social_data.get('sentiment_score', 0.5)) * 100,
                earnings_score=50.0,  # Default for now
                timestamp=datetime.now(),
                target_timeframe=f"{estimated_days} days",
                risk_factors=reasoning.risk_considerations,

                # Enhanced ML fields
                ml_confidence=ml_confidence,
                ml_model_version="enhanced_v1.0",
                top_features=self._get_top_features(ml_details, features),
                prediction_method="Enhanced ML",

                # Relative confidence fields
                confidence_level=relative_conf.level,
                confidence_emoji=relative_conf.emoji,
                confidence_description=relative_conf.description,
                raw_confidence=raw_confidence,
                percentile_rank=relative_conf.percentile,

                # Enhanced analysis fields
                economic_impact={
                    'overall_score': economic_analysis.overall_economic_score,
                    'insider_sentiment': economic_analysis.insider_sentiment_score,
                    'institutional_flow': economic_analysis.institutional_flow_score,
                    'macro_score': economic_analysis.macro_economic_score,
                    'confidence': economic_analysis.overall_confidence,
                    'risk_factors': economic_analysis.risk_factors,
                    'bullish_catalysts': economic_analysis.bullish_catalysts,
                    'bearish_catalysts': economic_analysis.bearish_catalysts
                },
                insider_analysis={
                    'insider_sentiment': insider_analysis.insider_sentiment_score,
                    'political_sentiment': insider_analysis.political_sentiment_score,
                    'institutional_flow': insider_analysis.institutional_flow_score,
                    'confidence_boost': insider_analysis.confidence_boost,
                    'key_insights': insider_analysis.key_insights
                },
                squeeze_potential={
                    'probability': squeeze_signal.squeeze_probability if squeeze_signal else 0,
                    'short_interest_ratio': squeeze_signal.short_interest_ratio if squeeze_signal else 0,
                    'triggers': squeeze_signal.key_triggers if squeeze_signal else [],
                    'risks': squeeze_signal.risk_factors if squeeze_signal else []
                } if squeeze_signal else None,
                target_range=target_range,
                estimated_days=estimated_days
            )

            logger.info(f"🚀 Generated enhanced bullish alert for {symbol}: {relative_conf.emoji} {relative_conf.level} {relative_conf.display_score}%")
            return alert

        except Exception as e:
            logger.error(f"❌ Error creating enhanced ML alert for {symbol}: {e}")
            return None

    async def _create_ml_alert(self, symbol: str, company_name: str, ml_confidence: float,
                              ml_details: Dict, features: Dict, technical_data: Dict, news_data: Dict) -> BullishAlert:
        """Create moon alert based on ML prediction."""
        try:
            # Generate ML-based reasons
            reasons = self._generate_ml_reasons(ml_details, features)
            risk_factors = self._identify_bullish_risks(technical_data, news_data)

            # Extract top contributing features
            top_features = ml_details.get('top_contributing_features', [])

            alert = BullishAlert(
                symbol=symbol,
                company_name=company_name or symbol,
                confidence=ml_confidence * 100,  # Convert to percentage
                reasons=reasons,
                technical_score=self._calculate_technical_bullish_score(technical_data),
                sentiment_score=features.get('news_sentiment', 0.0) * 100,
                social_score=features.get('social_sentiment', 0.0) * 100,
                earnings_score=0.0,  # Not used in ML model
                timestamp=datetime.now(),
                target_timeframe="1-3 days",
                risk_factors=risk_factors,
                # ML-specific fields
                ml_confidence=ml_confidence * 100,
                ml_model_version=ml_details.get('model_version', 'unknown'),
                top_features=top_features,
                prediction_method="ML",
                # Legacy confidence fields (for backward compatibility)
                confidence_level="MEDIUM",
                confidence_emoji="📈",
                confidence_description="ML-based prediction",
                raw_confidence=ml_confidence,
                percentile_rank=75.0,
                # Enhanced analysis fields (defaults for legacy method)
                economic_impact=None,
                insider_analysis=None,
                squeeze_potential=None,
                target_range=f"${features.get('close', 100):.2f} → ${features.get('close', 100) * 1.15:.2f} (15%)",
                estimated_days=3
            )

            logger.info(f"🚀 ML Bullish alert: {symbol} - {ml_confidence:.1%} confidence")
            return alert

        except Exception as e:
            logger.error(f"Failed to create ML alert: {e}")
            return None

    def _generate_ml_reasons(self, ml_details: Dict, features: Dict) -> List[str]:
        """Generate human-readable reasons based on ML prediction."""
        reasons = []

        # Add model confidence
        confidence = ml_details.get('raw_confidence', 0)
        reasons.append(f"ML model predicts {confidence:.1%} probability of +20% move in 1-3 days")

        # Add top contributing features
        top_features = ml_details.get('top_contributing_features', [])
        for feature_info in top_features[:3]:  # Top 3 features
            feature_name = feature_info['feature']
            importance = feature_info['importance']

            if importance > 0:
                if 'rsi' in feature_name.lower():
                    reasons.append(f"RSI indicates oversold conditions (bullish signal)")
                elif 'volume' in feature_name.lower():
                    reasons.append(f"Volume patterns suggest accumulation")
                elif 'macd' in feature_name.lower():
                    reasons.append(f"MACD momentum turning positive")
                elif 'bb' in feature_name.lower():
                    reasons.append(f"Bollinger Band position favorable for breakout")
                else:
                    reasons.append(f"Technical indicator {feature_name} shows bullish pattern")

        # Add model performance context
        model_accuracy = ml_details.get('model_accuracy', 0)
        if model_accuracy > 0:
            reasons.append(f"Model trained with {model_accuracy:.1%} historical accuracy")

        return reasons

    async def _analyze_with_rules(self, symbol: str, company_name: str, technical_data: Dict,
                                 news_data: Dict, social_data: Dict) -> Optional[BullishAlert]:
        """Fallback rule-based analysis when ML model is unavailable."""
        try:
            # Calculate rule-based scores
            bullish_scores = await self._calculate_bullish_scores(symbol, technical_data, news_data, social_data)

            # Calculate final confidence using bullish weights
            final_confidence = self._calculate_bullish_confidence(bullish_scores)

            # Only create alert if confidence exceeds threshold (lower threshold for fallback)
            fallback_threshold = 70.0  # Lower than ML threshold

            if final_confidence >= fallback_threshold:
                reasons = self._generate_bullish_reasons(bullish_scores, technical_data)
                risk_factors = self._identify_bullish_risks(technical_data, news_data)

                alert = BullishAlert(
                    symbol=symbol,
                    company_name=company_name or symbol,
                    confidence=final_confidence,
                    reasons=reasons,
                    technical_score=bullish_scores['technical'],
                    sentiment_score=bullish_scores['sentiment'],
                    social_score=bullish_scores['social'],
                    earnings_score=bullish_scores['earnings'],
                    timestamp=datetime.now(),
                    target_timeframe="1-3 days",
                    risk_factors=risk_factors,
                    # ML-specific fields (fallback values)
                    ml_confidence=0.0,
                    ml_model_version="rule-based-fallback",
                    top_features=[],
                    prediction_method="rule-based",
                    # Legacy confidence fields (for backward compatibility)
                    confidence_level="SPECULATIVE",
                    confidence_emoji="⚡",
                    confidence_description="Rule-based analysis",
                    raw_confidence=final_confidence / 100.0,
                    percentile_rank=50.0,
                    # Enhanced analysis fields (defaults for legacy method)
                    economic_impact=None,
                    insider_analysis=None,
                    squeeze_potential=None,
                    target_range=f"Rule-based target: +15-20%",
                    estimated_days=3
                )

                logger.info(f"🔄 Rule-based Bullish alert: {symbol} - {final_confidence:.1f}% confidence")
                return alert
            else:
                logger.debug(f"Rule-based confidence for {symbol} below threshold: {final_confidence:.1f}%")
                return None

        except Exception as e:
            logger.error(f"Rule-based analysis failed for {symbol}: {e}")
            return None

    async def _calculate_bullish_scores(self, symbol: str, technical_data: Dict,
                                      news_data: Dict, social_data: Dict) -> Dict[str, float]:
        """Calculate bullish-specific component scores"""
        scores = {}

        # Technical score (focus on oversold + volume surge)
        scores['technical'] = self._calculate_technical_bullish_score(technical_data)

        # Sentiment score (positive news sentiment)
        scores['sentiment'] = self._calculate_sentiment_bullish_score(news_data)

        # Social score (bullish social sentiment, CEO activity)
        scores['social'] = self._calculate_social_bullish_score(social_data)

        # Earnings score (upcoming positive catalysts)
        scores['earnings'] = await self._calculate_earnings_bullish_score(symbol)

        return scores

    def _calculate_technical_bullish_score(self, technical_data: Dict) -> float:
        """Calculate technical score for bullish potential"""
        score = 50.0  # Start neutral
        
        try:
            # RSI oversold condition (bullish signal)
            rsi = technical_data.get('rsi', {}).get('value', 50)
            if rsi < 30:
                score += 20  # Strong oversold signal
            elif rsi < 40:
                score += 10  # Moderate oversold
            elif rsi > 70:
                score -= 15  # Overbought is bearish for moon
                
            # MACD bullish signal
            macd_signal = technical_data.get('macd', {}).get('signal', 'neutral')
            if macd_signal == 'bullish':
                score += 15
            elif macd_signal == 'bearish':
                score -= 10
                
            # Volume surge (key for moon patterns)
            volume_data = technical_data.get('volume', {})
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                score += 20  # Strong volume surge
            elif volume_ratio > 1.5:
                score += 10  # Moderate volume increase
                
            # Bollinger Bands position
            bb_position = technical_data.get('bollinger_bands', {}).get('position', 'middle')
            if bb_position == 'below_lower':
                score += 15  # Oversold condition
            elif bb_position == 'lower_half':
                score += 5
                
            # Moving average trend
            ma_trend = technical_data.get('moving_averages', {}).get('trend', 'neutral')
            if ma_trend == 'bullish':
                score += 10
            elif ma_trend == 'bearish':
                score -= 5
                
        except Exception as e:
            logger.error(f"Error calculating technical bullish score: {e}")

        return np.clip(score, 0.0, 100.0)

    def _calculate_sentiment_bullish_score(self, news_data: Dict) -> float:
        """Calculate sentiment score for bullish potential"""
        score = 50.0  # Start neutral
        
        try:
            # News sentiment (positive is bullish signal)
            news_score = news_data.get('news_score', 50)
            if news_score > 70:
                score += 20  # Very positive news
            elif news_score > 60:
                score += 10  # Moderately positive
            elif news_score < 30:
                score -= 15  # Negative news
                
            # News volume/activity
            news_count = news_data.get('article_count', 0)
            if news_count > 10:
                score += 5  # High news activity
                
        except Exception as e:
            logger.error(f"Error calculating sentiment bullish score: {e}")

        return np.clip(score, 0.0, 100.0)

    def _calculate_social_bullish_score(self, social_data: Dict) -> float:
        """Calculate social score for bullish potential"""
        score = 50.0  # Start neutral
        
        try:
            # Social sentiment (positive is bullish signal)
            social_score = social_data.get('social_score', 50)
            if social_score > 70:
                score += 15  # Very positive social sentiment
            elif social_score > 60:
                score += 8   # Moderately positive
            elif social_score < 30:
                score -= 10  # Negative social sentiment
                
            # Social activity level
            mention_count = social_data.get('mention_count', 0)
            if mention_count > 100:
                score += 10  # High social activity
            elif mention_count > 50:
                score += 5   # Moderate activity
                
        except Exception as e:
            logger.error(f"Error calculating social bullish score: {e}")

        return np.clip(score, 0.0, 100.0)

    async def _calculate_earnings_bullish_score(self, symbol: str) -> float:
        """Calculate earnings score for bullish potential"""
        score = 50.0  # Start neutral
        
        try:
            # This would integrate with earnings calendar API
            # For now, simulate earnings impact
            
            # Check if earnings are upcoming (would boost bullish potential)
            # This is a placeholder - real implementation would check Finnhub API
            import random
            has_upcoming_earnings = random.choice([True, False])
            
            if has_upcoming_earnings:
                # Positive earnings expectations boost moon potential
                score += 15
                
        except Exception as e:
            logger.error(f"Error calculating earnings bullish score: {e}")

        return np.clip(score, 0.0, 100.0)

    def _calculate_bullish_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate final bullish confidence using weighted scores"""
        try:
            weighted_score = (
                scores['technical'] * (self.weights['technical'] / 100) +
                scores['sentiment'] * (self.weights['sentiment'] / 100) +
                scores['social'] * (self.weights['social'] / 100) +
                scores['earnings'] * (self.weights['earnings'] / 100)
            )
            
            return np.clip(weighted_score, 0.0, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating bullish confidence: {e}")
            return 50.0

    def _generate_bullish_reasons(self, scores: Dict[str, float], technical_data: Dict) -> List[str]:
        """Generate human-readable reasons for bullish alert"""
        reasons = []
        
        try:
            # Technical reasons
            if scores['technical'] > 70:
                rsi = technical_data.get('rsi', {}).get('value', 50)
                if rsi < 30:
                    reasons.append(f"Oversold RSI ({rsi:.1f}) suggests potential bounce")
                    
                volume_ratio = technical_data.get('volume', {}).get('volume_ratio', 1.0)
                if volume_ratio > 1.5:
                    reasons.append(f"Volume surge ({volume_ratio:.1f}x average) indicates interest")
                    
            # Sentiment reasons
            if scores['sentiment'] > 70:
                reasons.append("Positive news sentiment supports upward momentum")
                
            # Social reasons
            if scores['social'] > 70:
                reasons.append("Strong bullish social sentiment detected")
                
            # Earnings reasons
            if scores['earnings'] > 70:
                reasons.append("Upcoming earnings catalyst may drive price action")
                
            if not reasons:
                reasons.append("Multiple technical and sentiment factors align for potential move")
                
        except Exception as e:
            logger.error(f"Error generating bullish reasons: {e}")
            reasons = ["Pattern analysis suggests potential upward movement"]

        return reasons

    def _identify_bullish_risks(self, technical_data: Dict, news_data: Dict) -> List[str]:
        """Identify risk factors that could prevent bullish move"""
        risks = []
        
        try:
            # Technical risks
            rsi = technical_data.get('rsi', {}).get('value', 50)
            if rsi > 70:
                risks.append("Overbought RSI may limit upside potential")
                
            # Market risks
            risks.append("Market volatility could impact individual stock performance")
            risks.append("Pattern-based predictions have inherent uncertainty")
            
            # General disclaimer
            risks.append("Past patterns do not guarantee future results")
            
        except Exception as e:
            logger.error(f"Error identifying bullish risks: {e}")
            risks = ["General market and pattern recognition risks apply"]
            
        return risks

    def _calculate_enhanced_target_range(self, technical_data: Dict, relative_conf,
                                       economic_analysis, insider_analysis) -> str:
        """Calculate enhanced target range with multiple factors"""
        try:
            current_price = float(technical_data.get('current_price', 100))
            volatility = float(technical_data.get('volatility_10', 0.02))

            # Base target calculation
            if relative_conf.level == "HIGH":
                base_upside = 0.20  # 20% for high confidence
            elif relative_conf.level == "MEDIUM":
                base_upside = 0.15  # 15% for medium confidence
            else:
                base_upside = 0.10  # 10% for speculative

            # Adjust for volatility
            volatility_multiplier = 1 + (volatility * 10)  # Higher volatility = higher targets

            # Adjust for economic events
            economic_multiplier = 1.0
            if economic_analysis.overall_economic_score > 0.3:
                economic_multiplier = 1.1  # 10% boost for positive economic conditions
            elif economic_analysis.overall_economic_score < -0.3:
                economic_multiplier = 0.9  # 10% reduction for negative economic conditions

            # Adjust for insider activity
            insider_multiplier = 1.0
            if insider_analysis.confidence_boost > 5:
                insider_multiplier = 1.05  # 5% boost for strong insider buying
            elif insider_analysis.confidence_boost < -5:
                insider_multiplier = 0.95  # 5% reduction for insider selling

            # Calculate final target
            adjusted_upside = base_upside * volatility_multiplier * economic_multiplier * insider_multiplier
            target_price = current_price * (1 + adjusted_upside)

            return f"${current_price:.2f} → ${target_price:.2f} ({adjusted_upside:.1%})"

        except Exception as e:
            logger.error(f"Error calculating enhanced target range: {e}")
            return "Target calculation unavailable"

    def _calculate_enhanced_timeframe(self, features: Dict, relative_conf, economic_analysis) -> int:
        """Calculate enhanced timeframe estimation"""
        try:
            # Base timeframe
            if relative_conf.level == "HIGH":
                base_days = 2  # High confidence = faster moves
            elif relative_conf.level == "MEDIUM":
                base_days = 3  # Medium confidence = moderate timeframe
            else:
                base_days = 5  # Speculative = longer timeframe

            # Adjust for volume
            volume_ratio = features.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                base_days = max(1, base_days - 1)  # High volume = faster
            elif volume_ratio < 0.8:
                base_days += 1  # Low volume = slower

            # Adjust for economic events
            if len(economic_analysis.bullish_catalysts) > 0:
                base_days = max(1, base_days - 1)  # Bullish catalysts accelerate moves

            return min(7, max(1, base_days))  # Cap between 1-7 days

        except Exception as e:
            logger.error(f"Error calculating enhanced timeframe: {e}")
            return 3  # Default

    def _calculate_technical_score(self, technical_data: Dict) -> float:
        """Calculate technical analysis score"""
        try:
            score = 50.0  # Start neutral

            # RSI analysis
            rsi = float(technical_data.get('rsi', 50))
            if rsi < 30:
                score += 20  # Oversold
            elif rsi < 40:
                score += 10  # Approaching oversold
            elif rsi > 70:
                score -= 10  # Overbought

            # Volume analysis
            volume_ratio = float(technical_data.get('volume_ratio', 1.0))
            if volume_ratio > 1.5:
                score += 15  # Volume surge
            elif volume_ratio > 1.2:
                score += 8   # Moderate volume increase

            # MACD analysis
            macd_hist = float(technical_data.get('macd_histogram', 0))
            if macd_hist > 0:
                score += 10  # Bullish momentum

            return min(100, max(0, score))

        except Exception as e:
            logger.error(f"Error calculating technical score: {e}")
            return 50.0

    def _get_top_features(self, ml_details: Dict, features: Dict) -> List[Dict[str, Any]]:
        """Get top contributing features for transparency"""
        try:
            # This would use SHAP values in a real implementation
            # For now, return key features that influenced the decision
            top_features = []

            # Add key technical features
            if features.get('rsi_14', 50) < 30:
                top_features.append({
                    'name': 'RSI Oversold',
                    'value': features.get('rsi_14', 50),
                    'impact': 'Positive',
                    'description': 'RSI indicates oversold conditions'
                })

            if features.get('volume_ratio', 1.0) > 1.5:
                top_features.append({
                    'name': 'Volume Surge',
                    'value': features.get('volume_ratio', 1.0),
                    'impact': 'Positive',
                    'description': 'Volume significantly above average'
                })

            # Add AI features if available
            if features.get('grok_technical_score', 0) > 70:
                top_features.append({
                    'name': 'AI Technical Analysis',
                    'value': features.get('grok_technical_score', 0),
                    'impact': 'Positive',
                    'description': 'Grok AI identified strong technical setup'
                })

            return top_features[:5]  # Return top 5 features

        except Exception as e:
            logger.error(f"Error getting top features: {e}")
            return []


# Utility function for easy usage
async def analyze_bullish_potential(symbol: str, company_name: str = None) -> Optional[BullishAlert]:
    """Convenience function to analyze bullish potential"""
    async with BullishAnalyzer() as analyzer:
        return await analyzer.analyze_bullish_potential(symbol, company_name)
