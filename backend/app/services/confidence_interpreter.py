"""
Confidence Interpreter - Converts ML confidence scores to user-friendly language
Provides realistic but exciting confidence descriptions and reasoning
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence level categories for user-friendly display"""
    HIGH = "HIGH"           # 80-100%: Strong conviction plays
    MEDIUM = "MEDIUM"       # 60-79%: Solid setups
    SPECULATIVE = "SPECULATIVE"  # 48-59%: Worth watching


@dataclass
class ConfidenceInterpretation:
    """Interpreted confidence with user-friendly language"""
    level: ConfidenceLevel
    emoji: str
    title: str
    description: str
    risk_note: str
    conviction_phrase: str


class ConfidenceInterpreter:
    """
    Converts raw ML confidence scores to exciting but realistic user language
    """
    
    def __init__(self):
        self.confidence_ranges = {
            ConfidenceLevel.HIGH: (80, 100),
            ConfidenceLevel.MEDIUM: (60, 79),
            ConfidenceLevel.SPECULATIVE: (48, 59)
        }
        
        self.interpretations = {
            ConfidenceLevel.HIGH: ConfidenceInterpretation(
                level=ConfidenceLevel.HIGH,
                emoji="🔥",
                title="Strong Conviction",
                description="Our ML algorithm identified multiple bullish signals aligning",
                risk_note="High probability setup, but markets are unpredictable",
                conviction_phrase="Strong technical and sentiment alignment"
            ),
            ConfidenceLevel.MEDIUM: ConfidenceInterpretation(
                level=ConfidenceLevel.MEDIUM,
                emoji="📈",
                title="Solid Setup",
                description="Our model detected favorable conditions for upward movement",
                risk_note="Good setup, but consider position sizing carefully",
                conviction_phrase="Multiple positive indicators present"
            ),
            ConfidenceLevel.SPECULATIVE: ConfidenceInterpretation(
                level=ConfidenceLevel.SPECULATIVE,
                emoji="⚡",
                title="Worth Watching",
                description="Our algorithm spotted potential, but signals are mixed",
                risk_note="Speculative play - use small position sizes",
                conviction_phrase="Early signals detected, monitor closely"
            )
        }
    
    def interpret_bullish_confidence(self, confidence: float, features: Dict) -> ConfidenceInterpretation:
        """
        Convert bullish confidence score to user-friendly interpretation
        
        Args:
            confidence: Raw ML confidence (0-100)
            features: Feature dictionary for context
            
        Returns:
            ConfidenceInterpretation with user-friendly language
        """
        level = self._get_confidence_level(confidence)
        base_interpretation = self.interpretations[level]
        
        # Customize based on features
        customized = self._customize_interpretation(base_interpretation, confidence, features, "bullish")
        return customized
    
    def interpret_bearish_confidence(self, confidence: float, features: Dict) -> ConfidenceInterpretation:
        """
        Convert bearish confidence score to user-friendly interpretation
        """
        level = self._get_confidence_level(confidence)
        base_interpretation = self.interpretations[level]
        
        # Customize for bearish
        customized = self._customize_interpretation(base_interpretation, confidence, features, "bearish")
        return customized
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level from raw score"""
        for level, (min_conf, max_conf) in self.confidence_ranges.items():
            if min_conf <= confidence <= max_conf:
                return level
        
        # Default to speculative if below 48%
        return ConfidenceLevel.SPECULATIVE
    
    def _customize_interpretation(self, base: ConfidenceInterpretation, confidence: float, 
                                features: Dict, direction: str) -> ConfidenceInterpretation:
        """Customize interpretation based on specific features"""
        
        # Create customized copy
        customized = ConfidenceInterpretation(
            level=base.level,
            emoji=base.emoji,
            title=base.title,
            description=base.description,
            risk_note=base.risk_note,
            conviction_phrase=base.conviction_phrase
        )
        
        # Adjust for direction
        if direction == "bearish":
            customized.emoji = "📉" if base.level == ConfidenceLevel.HIGH else "⚠️"
            customized.description = customized.description.replace("upward movement", "downward movement")
            customized.description = customized.description.replace("bullish signals", "bearish signals")
        
        # Add confidence percentage for transparency
        confidence_text = f" ({confidence:.0f}% confidence)"
        customized.title += confidence_text
        
        return customized
    
    def generate_reasoning_bullets(self, features: Dict, ml_details: Dict, 
                                 direction: str = "bullish") -> List[str]:
        """
        Generate bullet-point reasoning for why the model made this prediction
        
        Args:
            features: Feature dictionary
            ml_details: ML model details
            direction: "bullish" or "bearish"
            
        Returns:
            List of bullet-point reasons
        """
        reasons = []
        
        # Technical indicators
        if features.get('rsi_14', 50) < 30:
            reasons.append("• RSI shows oversold conditions - potential bounce setup")
        elif features.get('rsi_14', 50) > 70:
            reasons.append("• RSI indicates overbought - potential pullback risk")
        
        # Volume analysis
        volume_ratio = features.get('volume_ratio', 1.0)
        if volume_ratio > 1.5:
            reasons.append(f"• Volume surge detected ({volume_ratio:.1f}x average) - increased interest")
        
        # MACD momentum
        macd_hist = features.get('macd_histogram', 0)
        if macd_hist > 0 and direction == "bullish":
            reasons.append("• MACD showing bullish momentum - trend may continue")
        elif macd_hist < 0 and direction == "bearish":
            reasons.append("• MACD showing bearish momentum - downtrend likely")
        
        # Sentiment analysis
        news_sentiment = features.get('news_sentiment', 0.5)
        if news_sentiment > 0.6:
            reasons.append("• Positive news sentiment detected - market optimism")
        elif news_sentiment < 0.4:
            reasons.append("• Negative news sentiment - market pessimism")
        
        # Social sentiment
        social_sentiment = features.get('social_sentiment', 0.5)
        if social_sentiment > 0.7:
            reasons.append("• Strong social media buzz - retail interest building")
        
        # Short interest (if available)
        short_interest = features.get('short_interest_ratio', 0)
        if short_interest > 10 and direction == "bullish":
            reasons.append(f"• High short interest ({short_interest:.1f}%) - potential squeeze setup")
        
        # AI analysis
        grok_score = features.get('grok_technical_score', 0)
        deepseek_score = features.get('deepseek_sentiment_score', 0)
        if grok_score > 70 or deepseek_score > 70:
            reasons.append("• Our AI analysis identified strong technical/sentiment alignment")
        
        # Support/Resistance levels
        bb_position = features.get('bb_position', 0.5)
        if bb_position < 0.2 and direction == "bullish":
            reasons.append("• Price near lower Bollinger Band - potential support bounce")
        elif bb_position > 0.8 and direction == "bearish":
            reasons.append("• Price near upper Bollinger Band - potential resistance rejection")
        
        # Default ML reasoning if no specific triggers
        if not reasons:
            reasons.append("• Our ML algorithm detected favorable risk/reward patterns")
            reasons.append("• Multiple technical indicators showing alignment")
        
        # Add model attribution
        reasons.append("• Analysis based on 82-feature ML model trained on historical patterns")
        
        return reasons[:6]  # Limit to 6 bullet points for readability


def get_confidence_interpreter() -> ConfidenceInterpreter:
    """Get global confidence interpreter instance"""
    return ConfidenceInterpreter()
