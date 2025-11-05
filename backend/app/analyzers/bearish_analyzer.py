"""
Bearish Analyzer - Identifies patterns for potential -20% stock drops
Reuses existing stock analyzer logic with bearish-specific scoring weights
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
from ..services.model_loader import predict_bearish_ml, get_model_loader
from ..core.redis_client import get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BearishAlert:
    """Alert for potential bearish (>20% drop) warning"""
    symbol: str
    company_name: str
    confidence: float
    reasons: List[str]
    technical_score: float
    sentiment_score: float
    social_score: float
    earnings_score: float
    timestamp: datetime
    target_timeframe: str  # "1-3 days"
    risk_factors: List[str]
    # ML-specific fields
    ml_confidence: float
    ml_model_version: str
    top_features: List[Dict[str, Any]]
    prediction_method: str  # "ML" or "rule-based"


class BearishAnalyzer:
    """
    Analyzer for identifying "When Bearish?" patterns.
    Focuses on overbought technicals, negative sentiment, and bearish signals.
    """
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.confidence_scorer = ConfidenceScorer()
        self.ai_consensus = AIConsensusEngine()
        self.redis_client = None
        self.use_ml_model = True  # Primary method: ML model
        self.ml_confidence_threshold = 0.75  # Conservative threshold for 2024 data
        
        # Rug-specific scoring weights (total = 100%)
        self.weights = {
            "technical": 40.0,    # Technical indicators (RSI, MACD, volume)
            "sentiment": 30.0,    # News and social sentiment
            "earnings": 20.0,     # Earnings expectations and calendar
            "social": 10.0        # CEO activity, social mentions
        }
        
        # Rug pattern thresholds
        self.confidence_threshold = 70.0  # Only alert if >70% confidence
        self.rsi_overbought_threshold = 70.0
        self.volume_surge_threshold = 1.5  # 1.5x average volume
        self.negative_sentiment_threshold = -0.3
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.redis_client = await get_redis_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.redis_client:
            await self.redis_client.close()

    async def analyze_bearish_potential(self, symbol: str, company_name: str = None) -> Optional[BearishAlert]:
        """
        Analyze a symbol for rug potential using trained ML model with rule-based fallback.

        Args:
            symbol: Stock symbol to analyze
            company_name: Company name (optional)

        Returns:
            BearishAlert if confidence > threshold, None otherwise
        """
        try:
            # Use existing confidence scorer for comprehensive analysis
            analysis_result = await self.confidence_scorer.analyze_symbol(
                symbol, company_name or symbol
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

                    # Use ML confidence if above threshold
                    if ml_confidence >= self.ml_confidence_threshold:
                        return await self._create_ml_alert(
                            symbol, company_name, ml_confidence, ml_details, features,
                            technical_data, news_data
                        )
                    else:
                        logger.info(f"💥 {symbol}: ML confidence {ml_confidence:.1%} below threshold {self.ml_confidence_threshold:.0%}")

            # Fallback to rule-based analysis
            logger.info(f"🔄 {symbol}: Using rule-based fallback analysis")
            return await self._analyze_with_rules(symbol, company_name, technical_data, news_data, social_data)
            # This code is now handled by the new ML/rule-based methods above
            return None
                
        except Exception as e:
            logger.error(f"Error analyzing rug potential for {symbol}: {e}")
            return None

    async def _predict_with_ml_model(self, technical_data: Dict, news_data: Dict, social_data: Dict) -> Optional[Tuple[float, Dict, Dict]]:
        """
        Use trained ML model to predict rug potential.

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
            ml_confidence, ml_details = await predict_bearish_ml(features)

            logger.info(f"🤖 ML rug prediction: {ml_confidence:.1%} confidence")

            return ml_confidence, ml_details, features

        except Exception as e:
            logger.error(f"ML rug prediction failed: {e}")
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

    async def _create_ml_alert(self, symbol: str, company_name: str, ml_confidence: float,
                              ml_details: Dict, features: Dict, technical_data: Dict, news_data: Dict) -> BearishAlert:
        """Create rug alert based on ML prediction."""
        try:
            # Generate ML-based reasons
            reasons = self._generate_ml_reasons(ml_details, features)
            risk_factors = self._identify_rug_risks(technical_data, news_data)

            # Extract top contributing features
            top_features = ml_details.get('top_contributing_features', [])

            alert = BearishAlert(
                symbol=symbol,
                company_name=company_name or symbol,
                confidence=ml_confidence * 100,  # Convert to percentage
                reasons=reasons,
                technical_score=self._calculate_technical_rug_score(technical_data),
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
                prediction_method="ML"
            )

            logger.info(f"💥 ML Rug alert: {symbol} - {ml_confidence:.1%} confidence")
            return alert

        except Exception as e:
            logger.error(f"Failed to create ML rug alert: {e}")
            return None

    def _generate_ml_reasons(self, ml_details: Dict, features: Dict) -> List[str]:
        """Generate human-readable reasons based on ML rug prediction."""
        reasons = []

        # Add model confidence
        confidence = ml_details.get('raw_confidence', 0)
        reasons.append(f"ML model predicts {confidence:.1%} probability of -20% drop in 1-3 days")

        # Add top contributing features
        top_features = ml_details.get('top_contributing_features', [])
        for feature_info in top_features[:3]:  # Top 3 features
            feature_name = feature_info['feature']
            importance = feature_info['importance']

            if importance > 0:
                if 'rsi' in feature_name.lower():
                    reasons.append(f"RSI indicates overbought conditions (bearish signal)")
                elif 'volume' in feature_name.lower():
                    reasons.append(f"Volume patterns suggest distribution")
                elif 'macd' in feature_name.lower():
                    reasons.append(f"MACD momentum turning negative")
                elif 'bb' in feature_name.lower():
                    reasons.append(f"Bollinger Band position suggests breakdown risk")
                else:
                    reasons.append(f"Technical indicator {feature_name} shows bearish pattern")

        # Add model performance context
        model_accuracy = ml_details.get('model_accuracy', 0)
        if model_accuracy > 0:
            reasons.append(f"Model trained with {model_accuracy:.1%} historical accuracy")

        return reasons

    async def _analyze_with_rules(self, symbol: str, company_name: str, technical_data: Dict,
                                 news_data: Dict, social_data: Dict) -> Optional[BearishAlert]:
        """Fallback rule-based analysis when ML model is unavailable."""
        try:
            # Calculate rule-based scores
            rug_scores = await self._calculate_rug_scores(symbol, technical_data, news_data, social_data)

            # Calculate final confidence using rug weights
            final_confidence = self._calculate_rug_confidence(rug_scores)

            # Only create alert if confidence exceeds threshold (lower threshold for fallback)
            fallback_threshold = 70.0  # Lower than ML threshold

            if final_confidence >= fallback_threshold:
                reasons = self._generate_rug_reasons(rug_scores, technical_data)
                risk_factors = self._identify_rug_risks(technical_data, news_data)

                alert = BearishAlert(
                    symbol=symbol,
                    company_name=company_name or symbol,
                    confidence=final_confidence,
                    reasons=reasons,
                    technical_score=rug_scores['technical'],
                    sentiment_score=rug_scores['sentiment'],
                    social_score=rug_scores['social'],
                    earnings_score=rug_scores['earnings'],
                    timestamp=datetime.now(),
                    target_timeframe="1-3 days",
                    risk_factors=risk_factors,
                    # ML-specific fields (fallback values)
                    ml_confidence=0.0,
                    ml_model_version="rule-based-fallback",
                    top_features=[],
                    prediction_method="rule-based"
                )

                logger.info(f"🔄 Rule-based Rug alert: {symbol} - {final_confidence:.1f}% confidence")
                return alert
            else:
                logger.debug(f"Rule-based rug confidence for {symbol} below threshold: {final_confidence:.1f}%")
                return None

        except Exception as e:
            logger.error(f"Rule-based rug analysis failed for {symbol}: {e}")
            return None

    async def _calculate_rug_scores(self, symbol: str, technical_data: Dict, 
                                  news_data: Dict, social_data: Dict) -> Dict[str, float]:
        """Calculate rug-specific component scores"""
        scores = {}
        
        # Technical score (focus on overbought + bearish signals)
        scores['technical'] = self._calculate_technical_rug_score(technical_data)
        
        # Sentiment score (negative news sentiment)
        scores['sentiment'] = self._calculate_sentiment_rug_score(news_data)
        
        # Social score (bearish social sentiment, quiet CEO activity)
        scores['social'] = self._calculate_social_rug_score(social_data)
        
        # Earnings score (negative catalysts, earnings misses)
        scores['earnings'] = await self._calculate_earnings_rug_score(symbol)
        
        return scores

    def _calculate_technical_rug_score(self, technical_data: Dict) -> float:
        """Calculate technical score for rug potential"""
        score = 50.0  # Start neutral
        
        try:
            # RSI overbought condition (bearish for rug)
            rsi = technical_data.get('rsi', {}).get('value', 50)
            if rsi > 70:
                score += 20  # Strong overbought signal
            elif rsi > 60:
                score += 10  # Moderate overbought
            elif rsi < 30:
                score -= 15  # Oversold is bullish, reduces rug potential
                
            # MACD bearish signal
            macd_signal = technical_data.get('macd', {}).get('signal', 'neutral')
            if macd_signal == 'bearish':
                score += 15
            elif macd_signal == 'bullish':
                score -= 10
                
            # Volume surge (can indicate selling pressure)
            volume_data = technical_data.get('volume', {})
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                score += 15  # High volume could be selling
            elif volume_ratio > 1.5:
                score += 8   # Moderate volume increase
                
            # Bollinger Bands position
            bb_position = technical_data.get('bollinger_bands', {}).get('position', 'middle')
            if bb_position == 'above_upper':
                score += 15  # Overbought condition
            elif bb_position == 'upper_half':
                score += 5
                
            # Moving average trend
            ma_trend = technical_data.get('moving_averages', {}).get('trend', 'neutral')
            if ma_trend == 'bearish':
                score += 10
            elif ma_trend == 'bullish':
                score -= 5
                
        except Exception as e:
            logger.error(f"Error calculating technical rug score: {e}")
            
        return np.clip(score, 0.0, 100.0)

    def _calculate_sentiment_rug_score(self, news_data: Dict) -> float:
        """Calculate sentiment score for rug potential"""
        score = 50.0  # Start neutral
        
        try:
            # News sentiment (negative is bearish for rug)
            news_score = news_data.get('news_score', 50)
            if news_score < 30:
                score += 20  # Very negative news
            elif news_score < 40:
                score += 10  # Moderately negative
            elif news_score > 70:
                score -= 15  # Positive news reduces rug potential
                
            # News volume/activity (negative news gets more attention)
            news_count = news_data.get('article_count', 0)
            if news_count > 10 and news_score < 40:
                score += 5  # High negative news activity
                
        except Exception as e:
            logger.error(f"Error calculating sentiment rug score: {e}")
            
        return np.clip(score, 0.0, 100.0)

    def _calculate_social_rug_score(self, social_data: Dict) -> float:
        """Calculate social score for rug potential"""
        score = 50.0  # Start neutral
        
        try:
            # Social sentiment (negative is bearish for rug)
            social_score = social_data.get('social_score', 50)
            if social_score < 30:
                score += 15  # Very negative social sentiment
            elif social_score < 40:
                score += 8   # Moderately negative
            elif social_score > 70:
                score -= 10  # Positive social sentiment reduces rug potential
                
            # Social activity level (high activity with negative sentiment)
            mention_count = social_data.get('mention_count', 0)
            if mention_count > 100 and social_score < 40:
                score += 10  # High negative social activity
            elif mention_count > 50 and social_score < 40:
                score += 5   # Moderate negative activity
                
        except Exception as e:
            logger.error(f"Error calculating social rug score: {e}")
            
        return np.clip(score, 0.0, 100.0)

    async def _calculate_earnings_rug_score(self, symbol: str) -> float:
        """Calculate earnings score for rug potential"""
        score = 50.0  # Start neutral
        
        try:
            # This would integrate with earnings calendar API
            # For now, simulate earnings impact
            
            # Check if earnings are upcoming with negative expectations
            # This is a placeholder - real implementation would check Finnhub API
            import random
            has_upcoming_earnings = random.choice([True, False])
            earnings_sentiment = random.choice(['positive', 'negative', 'neutral'])
            
            if has_upcoming_earnings and earnings_sentiment == 'negative':
                # Negative earnings expectations boost rug potential
                score += 15
            elif has_upcoming_earnings and earnings_sentiment == 'positive':
                # Positive earnings expectations reduce rug potential
                score -= 10
                
        except Exception as e:
            logger.error(f"Error calculating earnings rug score: {e}")
            
        return np.clip(score, 0.0, 100.0)

    def _calculate_rug_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate final rug confidence using weighted scores"""
        try:
            weighted_score = (
                scores['technical'] * (self.weights['technical'] / 100) +
                scores['sentiment'] * (self.weights['sentiment'] / 100) +
                scores['social'] * (self.weights['social'] / 100) +
                scores['earnings'] * (self.weights['earnings'] / 100)
            )
            
            return np.clip(weighted_score, 0.0, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating rug confidence: {e}")
            return 50.0

    def _generate_rug_reasons(self, scores: Dict[str, float], technical_data: Dict) -> List[str]:
        """Generate human-readable reasons for rug alert"""
        reasons = []
        
        try:
            # Technical reasons
            if scores['technical'] > 70:
                rsi = technical_data.get('rsi', {}).get('value', 50)
                if rsi > 70:
                    reasons.append(f"Overbought RSI ({rsi:.1f}) suggests potential correction")
                    
                volume_ratio = technical_data.get('volume', {}).get('volume_ratio', 1.0)
                if volume_ratio > 1.5:
                    reasons.append(f"Volume surge ({volume_ratio:.1f}x average) may indicate selling pressure")
                    
            # Sentiment reasons
            if scores['sentiment'] > 70:
                reasons.append("Negative news sentiment creates downward pressure")
                
            # Social reasons
            if scores['social'] > 70:
                reasons.append("Bearish social sentiment detected")
                
            # Earnings reasons
            if scores['earnings'] > 70:
                reasons.append("Negative earnings expectations may trigger selloff")
                
            if not reasons:
                reasons.append("Multiple technical and sentiment factors align for potential decline")
                
        except Exception as e:
            logger.error(f"Error generating rug reasons: {e}")
            reasons = ["Pattern analysis suggests potential downward movement"]
            
        return reasons

    def _identify_rug_risks(self, technical_data: Dict, news_data: Dict) -> List[str]:
        """Identify risk factors that could prevent rug"""
        risks = []
        
        try:
            # Technical risks
            rsi = technical_data.get('rsi', {}).get('value', 50)
            if rsi < 30:
                risks.append("Oversold RSI may provide support and limit downside")
                
            # Market risks
            risks.append("Market support levels could prevent significant decline")
            risks.append("Pattern-based predictions have inherent uncertainty")
            
            # General disclaimer
            risks.append("Past patterns do not guarantee future results")
            
        except Exception as e:
            logger.error(f"Error identifying rug risks: {e}")
            risks = ["General market and pattern recognition risks apply"]
            
        return risks


# Utility function for easy usage
async def analyze_bearish_potential(symbol: str, company_name: str = None) -> Optional[BearishAlert]:
    """Convenience function to analyze bearish potential"""
    async with BearishAnalyzer() as analyzer:
        return await analyzer.analyze_bearish_potential(symbol, company_name)
