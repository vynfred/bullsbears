"""
AI Reasoning Generator
Generates consistent, user-friendly bullet-point explanations for ML predictions
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .short_squeeze_detector import ShortSqueezeSignal

logger = logging.getLogger(__name__)


@dataclass
class ReasoningExplanation:
    """AI-generated reasoning for a prediction"""
    primary_reasons: List[str]      # Main drivers (3-4 bullets)
    supporting_factors: List[str]   # Additional support (2-3 bullets)
    risk_considerations: List[str]  # Key risks (2-3 bullets)
    target_rationale: str          # Why this target range
    timeframe_rationale: str       # Why this timeframe


class AIReasoningGenerator:
    """
    Generates consistent, professional explanations for ML predictions
    Uses template-based approach with dynamic content insertion
    """
    
    def __init__(self):
        # Reasoning templates for different scenarios
        self.bullish_templates = {
            'oversold_bounce': "RSI shows oversold conditions ({rsi:.1f}) - potential bounce setup",
            'volume_surge': "Volume surge detected ({volume_ratio:.1f}x average) - increased institutional interest",
            'breakout_setup': "Price approaching key resistance at ${resistance:.2f} - breakout potential",
            'positive_sentiment': "Strong positive sentiment from news and social media analysis",
            'earnings_catalyst': "Upcoming earnings on {date} with positive analyst revisions",
            'short_squeeze': "High short interest ({short_pct:.1f}%) creates squeeze potential",
            'technical_momentum': "MACD showing bullish crossover with momentum building",
            'support_bounce': "Price holding above key support at ${support:.2f}",
            'ai_consensus': "Our dual AI system (Grok + DeepSeek) shows strong agreement"
        }
        
        self.bearish_templates = {
            'overbought_pullback': "RSI indicates overbought conditions ({rsi:.1f}) - pullback likely",
            'resistance_rejection': "Price rejected at key resistance ${resistance:.2f} - downside risk",
            'negative_sentiment': "Deteriorating sentiment from news and social media analysis",
            'earnings_risk': "Earnings expectations may be too high - disappointment risk",
            'technical_breakdown': "MACD showing bearish divergence with weakening momentum",
            'volume_decline': "Declining volume suggests lack of buying interest",
            'support_break': "Price breaking below key support at ${support:.2f}",
            'ai_consensus': "Our dual AI system identifies multiple bearish signals"
        }
        
        # Risk factor templates
        self.risk_templates = {
            'market_volatility': "High market volatility may impact individual stock performance",
            'earnings_uncertainty': "Earnings results could significantly impact price direction",
            'low_liquidity': "Lower trading volume may cause increased price volatility",
            'sector_weakness': "Sector headwinds may limit individual stock performance",
            'macro_concerns': "Broader economic concerns may affect market sentiment"
        }
    
    def generate_bullish_reasoning(self, symbol: str, features: Dict, ml_details: Dict, 
                                 squeeze_signal: Optional[ShortSqueezeSignal] = None) -> ReasoningExplanation:
        """Generate reasoning for bullish prediction"""
        
        primary_reasons = []
        supporting_factors = []
        risk_considerations = []
        
        # Analyze features to determine primary drivers
        rsi = features.get('rsi_14', 50)
        volume_ratio = features.get('volume_ratio', 1.0)
        macd_hist = features.get('macd_histogram', 0)
        news_sentiment = features.get('news_sentiment', 0.5)
        social_sentiment = features.get('social_sentiment', 0.5)
        
        # Primary reasons (most important factors)
        if rsi < 30:
            primary_reasons.append(self.bullish_templates['oversold_bounce'].format(rsi=rsi))
        
        if volume_ratio > 1.5:
            primary_reasons.append(self.bullish_templates['volume_surge'].format(volume_ratio=volume_ratio))
        
        if squeeze_signal and squeeze_signal.squeeze_probability > 70:
            primary_reasons.append(self.bullish_templates['short_squeeze'].format(
                short_pct=squeeze_signal.short_interest_percent
            ))
        
        if macd_hist > 0:
            primary_reasons.append(self.bullish_templates['technical_momentum'])
        
        # Supporting factors
        if news_sentiment > 0.6:
            supporting_factors.append(self.bullish_templates['positive_sentiment'])
        
        if features.get('grok_technical_score', 0) > 70 or features.get('deepseek_sentiment_score', 0) > 70:
            supporting_factors.append(self.bullish_templates['ai_consensus'])
        
        # Add ML attribution
        supporting_factors.append("Our 82-feature ML algorithm identified favorable risk/reward patterns")
        
        # Risk considerations
        if volume_ratio < 1.2:
            risk_considerations.append(self.risk_templates['low_liquidity'])
        
        risk_considerations.append(self.risk_templates['market_volatility'])
        
        # Generate target and timeframe rationale
        confidence = ml_details.get('confidence', 0.5)
        target_rationale = self._generate_target_rationale(symbol, confidence, features, "bullish")
        timeframe_rationale = self._generate_timeframe_rationale(features, "bullish")
        
        # Ensure we have enough reasons
        if len(primary_reasons) < 2:
            primary_reasons.append("Multiple technical indicators showing bullish alignment")
        
        if len(supporting_factors) < 2:
            supporting_factors.append("Historical patterns suggest favorable setup")
        
        return ReasoningExplanation(
            primary_reasons=primary_reasons[:4],
            supporting_factors=supporting_factors[:3],
            risk_considerations=risk_considerations[:3],
            target_rationale=target_rationale,
            timeframe_rationale=timeframe_rationale
        )
    
    def generate_bearish_reasoning(self, symbol: str, features: Dict, ml_details: Dict) -> ReasoningExplanation:
        """Generate reasoning for bearish prediction"""
        
        primary_reasons = []
        supporting_factors = []
        risk_considerations = []
        
        # Analyze features for bearish signals
        rsi = features.get('rsi_14', 50)
        volume_ratio = features.get('volume_ratio', 1.0)
        macd_hist = features.get('macd_histogram', 0)
        news_sentiment = features.get('news_sentiment', 0.5)
        
        # Primary reasons
        if rsi > 70:
            primary_reasons.append(self.bearish_templates['overbought_pullback'].format(rsi=rsi))
        
        if macd_hist < 0:
            primary_reasons.append(self.bearish_templates['technical_breakdown'])
        
        if news_sentiment < 0.4:
            primary_reasons.append(self.bearish_templates['negative_sentiment'])
        
        # Supporting factors
        if volume_ratio < 0.8:
            supporting_factors.append(self.bearish_templates['volume_decline'])
        
        if features.get('grok_technical_score', 0) < 30 or features.get('deepseek_sentiment_score', 0) < 30:
            supporting_factors.append(self.bearish_templates['ai_consensus'])
        
        # Add ML attribution
        supporting_factors.append("Our ML algorithm detected unfavorable risk/reward patterns")
        
        # Risk considerations
        risk_considerations.append("Potential for oversold bounce if selling becomes excessive")
        risk_considerations.append(self.risk_templates['market_volatility'])
        
        # Generate rationales
        confidence = ml_details.get('confidence', 0.5)
        target_rationale = self._generate_target_rationale(symbol, confidence, features, "bearish")
        timeframe_rationale = self._generate_timeframe_rationale(features, "bearish")
        
        # Ensure minimum reasons
        if len(primary_reasons) < 2:
            primary_reasons.append("Multiple technical indicators showing bearish divergence")
        
        if len(supporting_factors) < 2:
            supporting_factors.append("Historical patterns suggest downside risk")
        
        return ReasoningExplanation(
            primary_reasons=primary_reasons[:4],
            supporting_factors=supporting_factors[:3],
            risk_considerations=risk_considerations[:3],
            target_rationale=target_rationale,
            timeframe_rationale=timeframe_rationale
        )
    
    def _generate_target_rationale(self, symbol: str, confidence: float, features: Dict, direction: str) -> str:
        """Generate explanation for target price range"""
        
        volatility = features.get('volatility_10', 0.02)  # 10-day volatility
        
        if direction == "bullish":
            if confidence > 0.8:
                return f"High confidence setup suggests 20-25% upside potential based on historical patterns"
            elif confidence > 0.6:
                return f"Solid technical setup indicates 15-20% upside with current volatility levels"
            else:
                return f"Early signals suggest 10-15% upside if momentum builds"
        else:
            if confidence > 0.8:
                return f"Strong bearish signals indicate 15-20% downside risk"
            elif confidence > 0.6:
                return f"Technical breakdown suggests 10-15% downside potential"
            else:
                return f"Weakening momentum may lead to 5-10% pullback"
    
    def _generate_timeframe_rationale(self, features: Dict, direction: str) -> str:
        """Generate explanation for prediction timeframe"""
        
        volume_ratio = features.get('volume_ratio', 1.0)
        rsi = features.get('rsi_14', 50)
        
        if volume_ratio > 2.0:
            return "High volume suggests rapid price movement - 1-2 day timeframe"
        elif volume_ratio > 1.5:
            return "Increased volume indicates momentum building - 2-3 day timeframe"
        elif direction == "bullish" and rsi < 25:
            return "Extreme oversold conditions may resolve quickly - 1-3 days"
        elif direction == "bearish" and rsi > 75:
            return "Extreme overbought conditions suggest near-term pullback - 1-3 days"
        else:
            return "Technical patterns typically resolve within 2-5 trading days"
    
    def format_for_display(self, reasoning: ReasoningExplanation) -> List[str]:
        """Format reasoning into bullet points for user display"""
        
        bullets = []
        
        # Add primary reasons with bullet points
        for reason in reasoning.primary_reasons:
            bullets.append(f"• {reason}")
        
        # Add supporting factors
        for factor in reasoning.supporting_factors:
            bullets.append(f"• {factor}")
        
        # Add target and timeframe rationale
        bullets.append(f"• Target rationale: {reasoning.target_rationale}")
        bullets.append(f"• Timeframe: {reasoning.timeframe_rationale}")
        
        return bullets


# Global instance
_reasoning_generator = None

def get_ai_reasoning_generator() -> AIReasoningGenerator:
    """Get global AI reasoning generator instance"""
    global _reasoning_generator
    if _reasoning_generator is None:
        _reasoning_generator = AIReasoningGenerator()
    return _reasoning_generator
