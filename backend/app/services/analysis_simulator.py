"""
Analysis Simulator Service for BullsBears.xyz
Generates realistic dual AI analysis results for historical data backfill
"""

import asyncio
import logging
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

from .historical_data import StockData, MarketContext
from ..models.analysis_results import AnalysisResult
from .ai_consensus import ConsensusResult, AgreementLevel

logger = logging.getLogger(__name__)

@dataclass
class SimulatedGrokAnalysis:
    """Simulated Grok technical analysis result."""
    technical_score: float  # 0.0 to 1.0
    confidence: float  # 0.6 to 0.95
    reasoning: str
    technical_indicators: Dict[str, float]
    risk_assessment: str
    
@dataclass
class SimulatedDeepSeekAnalysis:
    """Simulated DeepSeek sentiment analysis result."""
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.6 to 0.95
    reasoning: str
    news_sentiment: Dict[str, Any]
    social_sentiment: Dict[str, Any]
    narrative_context: str

class AnalysisSimulator:
    """
    Service for generating realistic dual AI analysis results.
    Creates varied scenarios for ML training and cost monitoring validation.
    """
    
    def __init__(self):
        # Realistic confidence ranges
        self.grok_confidence_range = (0.65, 0.92)
        self.deepseek_confidence_range = (0.62, 0.88)
        
        # Technical analysis templates
        self.technical_templates = {
            "bullish": [
                "Strong upward momentum with RSI showing bullish divergence",
                "Price breaking above key resistance levels with volume confirmation",
                "Golden cross formation with 20-day MA crossing above 50-day MA",
                "Bullish flag pattern completion with strong volume support",
                "MACD showing positive momentum with histogram expansion"
            ],
            "bearish": [
                "Bearish divergence in RSI while price makes new highs",
                "Price failing to hold key support levels with increasing volume",
                "Death cross formation with 20-day MA crossing below 50-day MA",
                "Head and shoulders pattern completion signaling reversal",
                "MACD showing negative momentum with histogram contraction"
            ],
            "neutral": [
                "Consolidation pattern with price trading in tight range",
                "Mixed technical signals requiring further confirmation",
                "Sideways trend with balanced buying and selling pressure",
                "Technical indicators showing conflicting signals",
                "Waiting for breakout direction from current trading range"
            ]
        }
        
        # Sentiment analysis templates
        self.sentiment_templates = {
            "positive": [
                "Strong positive sentiment across social media platforms",
                "Bullish news flow with analyst upgrades and positive earnings",
                "Institutional buying interest with increased call option activity",
                "Positive earnings surprise driving optimistic outlook",
                "Strong sector rotation into growth stocks"
            ],
            "negative": [
                "Bearish sentiment with increased put option activity",
                "Negative news flow with analyst downgrades and concerns",
                "Institutional selling pressure with insider selling activity",
                "Disappointing earnings results driving pessimistic outlook",
                "Sector rotation away from growth into defensive stocks"
            ],
            "mixed": [
                "Mixed sentiment with conflicting analyst opinions",
                "Balanced news flow with both positive and negative catalysts",
                "Neutral institutional positioning with wait-and-see approach",
                "Earnings results meeting expectations with mixed guidance",
                "Sector showing mixed performance with stock-specific drivers"
            ]
        }
    
    async def simulate_grok_analysis(self, 
                                   stock_data: StockData, 
                                   market_context: MarketContext,
                                   technical_indicators: Dict[str, float]) -> SimulatedGrokAnalysis:
        """
        Simulate Grok's technical analysis with realistic variations.
        
        Args:
            stock_data: Historical stock data
            market_context: Market context for analysis
            technical_indicators: Calculated technical indicators
            
        Returns:
            SimulatedGrokAnalysis with technical score and reasoning
        """
        try:
            # Determine technical bias based on indicators
            rsi = technical_indicators.get('rsi_14', 50.0)
            price_vs_sma20 = technical_indicators.get('price_vs_sma20', 0.0)
            volatility = technical_indicators.get('volatility_20d', 20.0)
            
            # Calculate technical score (0.0 to 1.0)
            technical_score = 0.5  # Base neutral score
            
            # RSI influence
            if rsi > 70:
                technical_score -= 0.15  # Overbought
            elif rsi < 30:
                technical_score += 0.15  # Oversold
            elif 40 <= rsi <= 60:
                technical_score += 0.05  # Neutral zone
            
            # Price vs moving average influence
            if price_vs_sma20 > 5:
                technical_score += 0.1  # Above MA
            elif price_vs_sma20 < -5:
                technical_score -= 0.1  # Below MA
            
            # Market context influence
            if market_context.market_trend == "bullish":
                technical_score += 0.08
            elif market_context.market_trend == "bearish":
                technical_score -= 0.08
            
            # Volatility influence
            if volatility > 30:
                technical_score -= 0.05  # High volatility = higher risk
            elif volatility < 15:
                technical_score += 0.03  # Low volatility = stability
            
            # Add some randomness for realistic variation
            technical_score += random.uniform(-0.1, 0.1)
            technical_score = max(0.0, min(1.0, technical_score))
            
            # Generate confidence based on signal strength
            signal_strength = abs(technical_score - 0.5) * 2  # 0 to 1
            base_confidence = 0.7 + (signal_strength * 0.2)  # 0.7 to 0.9
            confidence = random.uniform(
                max(self.grok_confidence_range[0], base_confidence - 0.05),
                min(self.grok_confidence_range[1], base_confidence + 0.05)
            )
            
            # Select appropriate reasoning template
            if technical_score > 0.6:
                bias = "bullish"
            elif technical_score < 0.4:
                bias = "bearish"
            else:
                bias = "neutral"
            
            reasoning = random.choice(self.technical_templates[bias])
            
            # Generate risk assessment
            if volatility > 30 or abs(price_vs_sma20) > 10:
                risk_assessment = "HIGH"
            elif volatility < 15 and abs(price_vs_sma20) < 3:
                risk_assessment = "LOW"
            else:
                risk_assessment = "MEDIUM"
            
            return SimulatedGrokAnalysis(
                technical_score=round(technical_score, 3),
                confidence=round(confidence, 3),
                reasoning=reasoning,
                technical_indicators=technical_indicators,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            logger.error(f"Error simulating Grok analysis: {e}")
            # Return fallback analysis
            return SimulatedGrokAnalysis(
                technical_score=0.5,
                confidence=0.75,
                reasoning="Technical analysis inconclusive due to mixed signals",
                technical_indicators=technical_indicators,
                risk_assessment="MEDIUM"
            )
    
    async def simulate_deepseek_analysis(self, 
                                       stock_data: StockData, 
                                       market_context: MarketContext) -> SimulatedDeepSeekAnalysis:
        """
        Simulate DeepSeek's sentiment analysis with realistic variations.
        
        Args:
            stock_data: Historical stock data
            market_context: Market context for analysis
            
        Returns:
            SimulatedDeepSeekAnalysis with sentiment score and reasoning
        """
        try:
            # Base sentiment score influenced by market context and sector
            sentiment_score = 0.0  # Base neutral
            
            # Market context influence
            if market_context.market_trend == "bullish":
                sentiment_score += random.uniform(0.2, 0.4)
            elif market_context.market_trend == "bearish":
                sentiment_score -= random.uniform(0.2, 0.4)
            
            # Sector-specific sentiment
            sector_performance = market_context.sector_performance.get(stock_data.sector, 0.0)
            sentiment_score += sector_performance * 0.02  # Convert % to sentiment
            
            # VIX influence (fear index)
            if market_context.vix_level > 30:
                sentiment_score -= 0.15  # High fear
            elif market_context.vix_level < 15:
                sentiment_score += 0.1   # Low fear
            
            # Add randomness for news/social factors
            sentiment_score += random.uniform(-0.2, 0.2)
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
            
            # Generate confidence based on sentiment strength
            sentiment_strength = abs(sentiment_score)
            base_confidence = 0.65 + (sentiment_strength * 0.2)
            confidence = random.uniform(
                max(self.deepseek_confidence_range[0], base_confidence - 0.05),
                min(self.deepseek_confidence_range[1], base_confidence + 0.05)
            )
            
            # Select appropriate reasoning template
            if sentiment_score > 0.3:
                bias = "positive"
            elif sentiment_score < -0.3:
                bias = "negative"
            else:
                bias = "mixed"
            
            reasoning = random.choice(self.sentiment_templates[bias])
            
            # Generate news and social sentiment details
            news_sentiment = {
                "overall_tone": bias,
                "article_count": random.randint(5, 25),
                "positive_mentions": random.randint(0, 15),
                "negative_mentions": random.randint(0, 10),
                "neutral_mentions": random.randint(2, 8)
            }
            
            social_sentiment = {
                "reddit_mentions": random.randint(10, 100),
                "twitter_mentions": random.randint(50, 500),
                "overall_tone": bias,
                "engagement_level": random.choice(["low", "medium", "high"])
            }
            
            # Generate narrative context
            narrative_contexts = [
                f"Market sentiment for {stock_data.sector} sector showing {bias} bias",
                f"Institutional interest in {stock_data.symbol} appears {bias}",
                f"Social media discussion around {stock_data.symbol} trending {bias}",
                f"Analyst sentiment for {stock_data.symbol} remains {bias}"
            ]
            narrative_context = random.choice(narrative_contexts)
            
            return SimulatedDeepSeekAnalysis(
                sentiment_score=round(sentiment_score, 3),
                confidence=round(confidence, 3),
                reasoning=reasoning,
                news_sentiment=news_sentiment,
                social_sentiment=social_sentiment,
                narrative_context=narrative_context
            )
            
        except Exception as e:
            logger.error(f"Error simulating DeepSeek analysis: {e}")
            # Return fallback analysis
            return SimulatedDeepSeekAnalysis(
                sentiment_score=0.0,
                confidence=0.7,
                reasoning="Sentiment analysis inconclusive due to mixed signals",
                news_sentiment={"overall_tone": "mixed", "article_count": 10},
                social_sentiment={"overall_tone": "mixed", "engagement_level": "medium"},
                narrative_context="Mixed sentiment signals across data sources"
            )

    async def simulate_consensus_result(self,
                                      grok_analysis: SimulatedGrokAnalysis,
                                      deepseek_analysis: SimulatedDeepSeekAnalysis) -> ConsensusResult:
        """
        Simulate consensus engine result based on Grok and DeepSeek analyses.

        Args:
            grok_analysis: Simulated Grok technical analysis
            deepseek_analysis: Simulated DeepSeek sentiment analysis

        Returns:
            ConsensusResult with agreement level and final confidence
        """
        try:
            # Convert scores to comparable scale (both 0-1)
            grok_normalized = grok_analysis.technical_score
            deepseek_normalized = (deepseek_analysis.sentiment_score + 1) / 2  # -1,1 to 0,1

            # Calculate agreement level based on score difference
            score_diff = abs(grok_normalized - deepseek_normalized)

            if score_diff <= 0.2:
                agreement_level = AgreementLevel.STRONG_AGREEMENT
                confidence_adjustment = 0.12  # 12% boost
            elif score_diff <= 0.5:
                agreement_level = AgreementLevel.PARTIAL_AGREEMENT
                confidence_adjustment = 0.0   # No adjustment
            else:
                agreement_level = AgreementLevel.STRONG_DISAGREEMENT
                confidence_adjustment = -0.15  # 15% penalty

            # Calculate consensus confidence
            avg_confidence = (grok_analysis.confidence + deepseek_analysis.confidence) / 2
            consensus_confidence = avg_confidence * (1 + confidence_adjustment)
            consensus_confidence = max(0.1, min(0.95, consensus_confidence))

            # Generate consensus reasoning
            if agreement_level == AgreementLevel.STRONG_AGREEMENT:
                consensus_reasoning = f"Strong agreement between technical and sentiment analysis. {grok_analysis.reasoning[:50]}... aligns with {deepseek_analysis.reasoning[:50]}..."
            elif agreement_level == AgreementLevel.PARTIAL_AGREEMENT:
                consensus_reasoning = f"Partial agreement with mixed signals. Technical analysis suggests {grok_analysis.reasoning[:30]}... while sentiment shows {deepseek_analysis.reasoning[:30]}..."
            else:
                consensus_reasoning = f"Disagreement between analyses. Technical: {grok_analysis.reasoning[:40]}... Sentiment: {deepseek_analysis.reasoning[:40]}... Recommend caution."

            return ConsensusResult(
                final_recommendation="HOLD",  # Default for simulations
                consensus_confidence=round(consensus_confidence, 3),
                agreement_level=agreement_level,
                grok_score=grok_analysis.confidence,
                deepseek_score=deepseek_analysis.confidence,
                confidence_adjustment=confidence_adjustment,
                reasoning=consensus_reasoning,
                risk_warning="Simulated analysis - not financial advice",
                social_news_bridge=0.5,  # Default correlation
                hybrid_validation_triggered=False
            )

        except Exception as e:
            logger.error(f"Error simulating consensus result: {e}")
            # Return fallback consensus
            return ConsensusResult(
                final_recommendation="HOLD",
                consensus_confidence=0.7,
                agreement_level=AgreementLevel.PARTIAL_AGREEMENT,
                grok_score=grok_analysis.confidence,
                deepseek_score=deepseek_analysis.confidence,
                confidence_adjustment=0.0,
                reasoning="Analysis completed with mixed signals",
                risk_warning="Simulated analysis - not financial advice",
                social_news_bridge=0.5,
                hybrid_validation_triggered=False
            )

    def simulate_api_costs(self,
                          grok_analysis: SimulatedGrokAnalysis,
                          deepseek_analysis: SimulatedDeepSeekAnalysis) -> Dict[str, Any]:
        """
        Simulate realistic API costs and usage patterns.

        Args:
            grok_analysis: Simulated Grok analysis
            deepseek_analysis: Simulated DeepSeek analysis

        Returns:
            Dictionary with cost breakdown and API usage statistics
        """
        # Simulate token usage based on analysis complexity
        grok_tokens = random.randint(100, 500)  # Grok token usage
        deepseek_tokens = random.randint(200, 800)  # DeepSeek token usage

        # Cost calculation (in cents)
        grok_cost = grok_tokens * 0.002  # 2¢ per analysis estimate
        deepseek_cost = deepseek_tokens * 0.001  # 1¢ per analysis estimate
        total_ai_cost = grok_cost + deepseek_cost

        # Simulate external API calls
        api_calls = {
            "alpha_vantage": random.randint(1, 3),  # Stock data calls
            "newsapi": random.randint(0, 2),        # News data calls
            "reddit": random.randint(0, 1),         # Social sentiment calls
            "twitter": random.randint(0, 1),        # Social sentiment calls
            "fmp": random.randint(0, 1)             # Financial data calls
        }

        total_api_calls = sum(api_calls.values())

        # Simulate data sources used
        data_sources = ["yfinance", "technical_analysis"]
        if api_calls["alpha_vantage"] > 0:
            data_sources.append("alpha_vantage")
        if api_calls["newsapi"] > 0:
            data_sources.append("newsapi")
        if api_calls["reddit"] > 0:
            data_sources.append("reddit")
        if api_calls["twitter"] > 0:
            data_sources.append("twitter")
        if api_calls["fmp"] > 0:
            data_sources.append("fmp")

        # Simulate cache hit probability (higher for repeated symbols)
        cache_hit = random.random() < 0.3  # 30% cache hit rate

        # Performance tier based on response time simulation
        response_time_ms = random.randint(80, 300)
        if response_time_ms < 150:
            performance_tier = "fast"
        elif response_time_ms < 250:
            performance_tier = "standard"
        else:
            performance_tier = "slow"

        return {
            "ai_cost_cents": round(total_ai_cost, 2),
            "grok_tokens": grok_tokens,
            "deepseek_tokens": deepseek_tokens,
            "grok_cost_cents": round(grok_cost, 2),
            "deepseek_cost_cents": round(deepseek_cost, 2),
            "api_calls_count": total_api_calls,
            "api_calls_breakdown": api_calls,
            "data_sources_used": data_sources,
            "cache_hit": cache_hit,
            "response_time_ms": response_time_ms,
            "performance_tier": performance_tier
        }

    async def generate_complete_analysis(self,
                                       stock_data: StockData,
                                       market_context: MarketContext,
                                       technical_indicators: Dict[str, float]) -> Dict[str, Any]:
        """
        Generate complete dual AI analysis simulation with cost tracking.

        Args:
            stock_data: Historical stock data
            market_context: Market context for analysis
            technical_indicators: Calculated technical indicators

        Returns:
            Complete analysis result with all components
        """
        try:
            # Simulate analysis timing
            start_time = datetime.now()

            # Generate Grok analysis
            grok_analysis = await self.simulate_grok_analysis(
                stock_data, market_context, technical_indicators
            )

            # Simulate processing delay
            await asyncio.sleep(random.uniform(0.05, 0.15))

            # Generate DeepSeek analysis
            deepseek_analysis = await self.simulate_deepseek_analysis(
                stock_data, market_context
            )

            # Simulate consensus processing
            await asyncio.sleep(random.uniform(0.02, 0.08))
            consensus_result = await self.simulate_consensus_result(
                grok_analysis, deepseek_analysis
            )

            # Calculate total processing time
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Generate cost simulation
            cost_data = self.simulate_api_costs(grok_analysis, deepseek_analysis)
            cost_data["response_time_ms"] = processing_time_ms

            # Create ML features for training
            ml_features = {
                "vix_level": market_context.vix_level,
                "spy_change": market_context.spy_change,
                "market_trend": market_context.market_trend,
                "volatility_regime": market_context.volatility_regime,
                "sector": stock_data.sector,
                **technical_indicators
            }

            return {
                "symbol": stock_data.symbol,
                "grok_analysis": asdict(grok_analysis),
                "deepseek_analysis": asdict(deepseek_analysis),
                "consensus_result": asdict(consensus_result),
                "cost_data": cost_data,
                "ml_features": ml_features,
                "market_context": asdict(market_context),
                "processing_time_ms": processing_time_ms,
                "timestamp": start_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating complete analysis for {stock_data.symbol}: {e}")
            raise
