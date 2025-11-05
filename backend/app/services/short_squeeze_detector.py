"""
Short Squeeze Detection System
Identifies potential short squeeze setups using short interest and social chatter
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ShortSqueezeSignal:
    """Short squeeze detection signal"""
    symbol: str
    short_interest_ratio: float      # Days to cover (short interest / avg volume)
    short_interest_percent: float    # % of float shorted
    social_chatter_score: float      # Social media buzz intensity (0-100)
    squeeze_probability: float       # Overall squeeze probability (0-100)
    key_triggers: List[str]          # What's driving the squeeze potential
    risk_factors: List[str]          # Risks to the squeeze thesis


class ShortSqueezeDetector:
    """
    Detects potential short squeeze setups by analyzing:
    1. Short interest metrics (days to cover, % of float)
    2. Social media chatter and sentiment
    3. Technical price action (volume, momentum)
    4. Options activity (gamma exposure)
    """
    
    def __init__(self):
        # Short squeeze thresholds
        self.high_short_interest_threshold = 15.0    # >15% of float
        self.high_days_to_cover_threshold = 5.0      # >5 days to cover
        self.social_buzz_threshold = 70.0            # High social activity
        self.volume_surge_threshold = 2.0            # 2x average volume
        
        # Squeeze probability weights
        self.weights = {
            'short_metrics': 40.0,      # Short interest data
            'social_sentiment': 30.0,   # Social media buzz
            'technical_setup': 20.0,    # Price/volume action
            'options_activity': 10.0    # Gamma/options flow
        }
    
    async def detect_squeeze_potential(self, symbol: str, market_data: Dict, 
                                     social_data: Dict, options_data: Dict = None) -> Optional[ShortSqueezeSignal]:
        """
        Analyze symbol for short squeeze potential
        
        Args:
            symbol: Stock symbol
            market_data: Price, volume, short interest data
            social_data: Social media sentiment and chatter
            options_data: Options flow and gamma exposure (optional)
            
        Returns:
            ShortSqueezeSignal if squeeze potential detected, None otherwise
        """
        try:
            # Extract short interest metrics
            short_metrics = self._analyze_short_metrics(market_data)
            if not short_metrics:
                return None
            
            # Analyze social chatter
            social_score = self._analyze_social_chatter(social_data)
            
            # Technical analysis
            technical_score = self._analyze_technical_setup(market_data)
            
            # Options analysis (if available)
            options_score = self._analyze_options_activity(options_data) if options_data else 0
            
            # Calculate overall squeeze probability
            squeeze_probability = self._calculate_squeeze_probability(
                short_metrics, social_score, technical_score, options_score
            )
            
            # Only return signal if probability is significant
            if squeeze_probability < 60.0:
                return None
            
            # Generate key triggers and risk factors
            triggers = self._identify_squeeze_triggers(short_metrics, social_score, technical_score, options_score)
            risks = self._identify_squeeze_risks(market_data, social_data)
            
            return ShortSqueezeSignal(
                symbol=symbol,
                short_interest_ratio=short_metrics['days_to_cover'],
                short_interest_percent=short_metrics['short_percent'],
                social_chatter_score=social_score,
                squeeze_probability=squeeze_probability,
                key_triggers=triggers,
                risk_factors=risks
            )
            
        except Exception as e:
            logger.error(f"Error detecting squeeze potential for {symbol}: {e}")
            return None
    
    def _analyze_short_metrics(self, market_data: Dict) -> Optional[Dict]:
        """Analyze short interest metrics"""
        try:
            short_interest = market_data.get('short_interest', 0)
            shares_outstanding = market_data.get('shares_outstanding', 0)
            avg_volume = market_data.get('avg_volume_10d', 0)
            
            if not all([short_interest, shares_outstanding, avg_volume]):
                return None
            
            # Calculate key metrics
            short_percent = (short_interest / shares_outstanding) * 100
            days_to_cover = short_interest / avg_volume if avg_volume > 0 else 0
            
            return {
                'short_interest': short_interest,
                'short_percent': short_percent,
                'days_to_cover': days_to_cover,
                'is_high_short': short_percent > self.high_short_interest_threshold,
                'is_high_days_to_cover': days_to_cover > self.high_days_to_cover_threshold
            }
            
        except Exception as e:
            logger.error(f"Error analyzing short metrics: {e}")
            return None
    
    def _analyze_social_chatter(self, social_data: Dict) -> float:
        """Analyze social media chatter intensity and sentiment"""
        try:
            # Social volume metrics
            mention_volume = social_data.get('mention_volume_24h', 0)
            mention_volume_avg = social_data.get('mention_volume_avg', 1)
            
            # Sentiment metrics
            bullish_sentiment = social_data.get('bullish_sentiment', 0.5)
            
            # Squeeze-specific keywords
            squeeze_keywords = social_data.get('squeeze_keywords', 0)  # "squeeze", "moon", "diamond hands"
            
            # Calculate social buzz score
            volume_multiplier = mention_volume / mention_volume_avg if mention_volume_avg > 0 else 1
            sentiment_boost = max(0, (bullish_sentiment - 0.5) * 2)  # 0-1 scale
            keyword_boost = min(squeeze_keywords / 10, 1.0)  # Cap at 1.0
            
            social_score = min(100, (volume_multiplier * 30 + sentiment_boost * 40 + keyword_boost * 30))
            
            return social_score
            
        except Exception as e:
            logger.error(f"Error analyzing social chatter: {e}")
            return 0.0
    
    def _analyze_technical_setup(self, market_data: Dict) -> float:
        """Analyze technical price action for squeeze setup"""
        try:
            # Volume analysis
            current_volume = market_data.get('volume', 0)
            avg_volume = market_data.get('avg_volume_10d', 1)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Price momentum
            price_change_1d = market_data.get('price_change_1d', 0)
            price_change_5d = market_data.get('price_change_5d', 0)
            
            # RSI for oversold bounce potential
            rsi = market_data.get('rsi_14', 50)
            
            # Technical score components
            volume_score = min(40, volume_ratio * 20)  # Volume surge
            momentum_score = min(30, max(0, price_change_1d * 10))  # Positive momentum
            oversold_score = max(0, (30 - rsi) * 0.5) if rsi < 30 else 0  # Oversold bounce
            
            technical_score = volume_score + momentum_score + oversold_score
            
            return min(100, technical_score)
            
        except Exception as e:
            logger.error(f"Error analyzing technical setup: {e}")
            return 0.0
    
    def _analyze_options_activity(self, options_data: Dict) -> float:
        """Analyze options activity for gamma squeeze potential"""
        try:
            if not options_data:
                return 0.0
            
            # Call/put ratio
            call_volume = options_data.get('call_volume', 0)
            put_volume = options_data.get('put_volume', 1)
            call_put_ratio = call_volume / put_volume if put_volume > 0 else 0
            
            # Gamma exposure
            gamma_exposure = options_data.get('gamma_exposure', 0)
            
            # Unusual options activity
            unusual_call_activity = options_data.get('unusual_call_activity', False)
            
            # Options score
            ratio_score = min(40, call_put_ratio * 20)  # High call/put ratio
            gamma_score = min(30, abs(gamma_exposure) * 10)  # High gamma exposure
            unusual_score = 30 if unusual_call_activity else 0
            
            options_score = ratio_score + gamma_score + unusual_score
            
            return min(100, options_score)
            
        except Exception as e:
            logger.error(f"Error analyzing options activity: {e}")
            return 0.0
    
    def _calculate_squeeze_probability(self, short_metrics: Dict, social_score: float, 
                                     technical_score: float, options_score: float) -> float:
        """Calculate overall short squeeze probability"""
        
        # Short metrics score
        short_score = 0
        if short_metrics['is_high_short']:
            short_score += 50
        if short_metrics['is_high_days_to_cover']:
            short_score += 30
        short_score += min(20, short_metrics['short_percent'])  # Additional points for very high short %
        
        # Weighted combination
        weighted_score = (
            short_score * self.weights['short_metrics'] / 100 +
            social_score * self.weights['social_sentiment'] / 100 +
            technical_score * self.weights['technical_setup'] / 100 +
            options_score * self.weights['options_activity'] / 100
        )
        
        return min(100, weighted_score)
    
    def _identify_squeeze_triggers(self, short_metrics: Dict, social_score: float, 
                                 technical_score: float, options_score: float) -> List[str]:
        """Identify key triggers for potential squeeze"""
        triggers = []
        
        if short_metrics['short_percent'] > 20:
            triggers.append(f"High short interest ({short_metrics['short_percent']:.1f}% of float)")
        
        if short_metrics['days_to_cover'] > 7:
            triggers.append(f"High days to cover ({short_metrics['days_to_cover']:.1f} days)")
        
        if social_score > 80:
            triggers.append("Intense social media buzz and bullish sentiment")
        
        if technical_score > 70:
            triggers.append("Strong technical setup with volume surge")
        
        if options_score > 60:
            triggers.append("Unusual call option activity detected")
        
        return triggers
    
    def _identify_squeeze_risks(self, market_data: Dict, social_data: Dict) -> List[str]:
        """Identify risks to squeeze thesis"""
        risks = []
        
        # Market cap risk
        market_cap = market_data.get('market_cap', 0)
        if market_cap > 10_000_000_000:  # $10B+
            risks.append("Large market cap may limit squeeze potential")
        
        # Liquidity risk
        avg_volume = market_data.get('avg_volume_10d', 0)
        if avg_volume < 1_000_000:
            risks.append("Low liquidity may cause extreme volatility")
        
        # Fundamental risk
        if market_data.get('pe_ratio', 0) > 50:
            risks.append("High valuation may limit upside potential")
        
        # Social sentiment risk
        if social_data.get('bearish_sentiment', 0) > 0.3:
            risks.append("Mixed social sentiment may dampen momentum")
        
        return risks


# Global instance
_squeeze_detector = None

def get_short_squeeze_detector() -> ShortSqueezeDetector:
    """Get global short squeeze detector instance"""
    global _squeeze_detector
    if _squeeze_detector is None:
        _squeeze_detector = ShortSqueezeDetector()
    return _squeeze_detector
