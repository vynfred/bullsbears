"""
AI Consensus Engine for BullsBears.xyz Dual AI System.
Orchestrates the scout → handoff → cross-review → consensus workflow.
Implements agreement thresholds, confidence adjustments, and hybrid validation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .grok_ai import GrokAIService, GrokAnalysis
from .deepseek_ai import DeepSeekAIService, DeepSeekSentimentAnalysis, DeepSeekNewsAnalysis
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class AgreementLevel(Enum):
    """Agreement levels between AI systems."""
    STRONG_AGREEMENT = "strong_agreement"      # ±0.2 difference
    PARTIAL_AGREEMENT = "partial_agreement"    # 0.2-0.5 difference  
    STRONG_DISAGREEMENT = "strong_disagreement" # >0.5 difference

@dataclass
class ConsensusResult:
    """Result of AI consensus analysis."""
    final_recommendation: str  # BUY, SELL, HOLD
    consensus_confidence: float  # 0-100 (adjusted based on agreement)
    agreement_level: AgreementLevel
    grok_score: float  # Grok's confidence score
    deepseek_score: float  # DeepSeek's sentiment score (converted to confidence)
    confidence_adjustment: float  # Boost/reduction applied
    reasoning: str  # Combined reasoning
    risk_warning: Optional[str]
    social_news_bridge: float  # DeepSeek's social-news correlation
    hybrid_validation_triggered: bool  # Whether validation was needed
    
    # Detailed breakdown for transparency
    technical_weight: float = 0.45  # 45% technical analysis (Grok)
    sentiment_weight: float = 0.35  # 35% sentiment analysis (DeepSeek)
    fundamental_weight: float = 0.20  # 20% fundamental factors

@dataclass
class SocialDataPacket:
    """Structured data packet for Grok → DeepSeek handoff."""
    symbol: str
    raw_sentiment: float
    mention_count: int
    themes: List[str]
    sources: Dict[str, int]  # source -> mention count
    confidence: float
    timestamp: datetime

class AIConsensusEngine:
    """Core consensus engine for dual AI system."""
    
    def __init__(self):
        self.grok_service = GrokAIService()
        self.deepseek_service = DeepSeekAIService()
        self.redis_client = None
        
        # Agreement thresholds
        self.strong_agreement_threshold = 0.2
        self.partial_agreement_threshold = 0.5
        
        # Confidence adjustments (10-15% as per spec)
        self.agreement_boost = 0.12  # 12% boost for strong agreement
        self.disagreement_penalty = 0.15  # 15% penalty for strong disagreement
        
        # Hybrid validation threshold
        self.validation_variance_threshold = 0.2
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.redis_client = await get_redis_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    async def analyze_with_consensus(self, 
                                   symbol: str, 
                                   all_data: Dict[str, Any], 
                                   base_confidence: float) -> Optional[ConsensusResult]:
        """
        Main consensus analysis workflow: scout → handoff → cross-review → consensus.
        
        Args:
            symbol: Stock symbol
            all_data: Complete market data package
            base_confidence: Initial confidence score
            
        Returns:
            ConsensusResult with final recommendation and detailed breakdown
        """
        try:
            logger.info(f"Starting dual AI consensus analysis for {symbol}")
            
            # Phase 1: Grok Social Scouting + Technical Analysis
            grok_analysis, social_packet = await self._grok_scout_phase(symbol, all_data, base_confidence)
            if not grok_analysis:
                logger.error(f"Grok analysis failed for {symbol}")
                return None
            
            # Phase 2: DeepSeek Handoff Processing (News + Social Refinement)
            news_analysis, refined_social = await self._deepseek_handoff_phase(symbol, all_data, social_packet)
            if not news_analysis or not refined_social:
                logger.error(f"DeepSeek analysis failed for {symbol}")
                return None
            
            # Phase 3: Cross-Review (Mutual AI Validation)
            cross_review_adjustments = await self._cross_review_phase(
                symbol, grok_analysis, news_analysis, refined_social
            )
            
            # Phase 4: Consensus Resolution
            consensus_result = await self._consensus_resolution_phase(
                symbol, grok_analysis, news_analysis, refined_social, cross_review_adjustments
            )
            
            # Phase 5: Hybrid Validation (if needed)
            final_result = await self._hybrid_validation_phase(symbol, consensus_result, all_data)
            
            logger.info(f"Consensus analysis complete for {symbol}: {final_result.final_recommendation} "
                       f"({final_result.consensus_confidence:.1f}% confidence, {final_result.agreement_level.value})")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error in consensus analysis for {symbol}: {e}")
            return None
    
    async def _grok_scout_phase(self, symbol: str, all_data: Dict[str, Any], 
                               base_confidence: float) -> Tuple[Optional[GrokAnalysis], Optional[SocialDataPacket]]:
        """Phase 1: Grok scouting for social sentiment and technical analysis."""
        try:
            async with self.grok_service as grok:
                # Get comprehensive Grok analysis
                grok_analysis = await grok.analyze_comprehensive_option_play(symbol, all_data, base_confidence)
                
                # Create social data packet for DeepSeek handoff
                social_data = all_data.get('social', {})
                social_packet = SocialDataPacket(
                    symbol=symbol,
                    raw_sentiment=social_data.get('sentiment_score', 0.0),
                    mention_count=social_data.get('mention_count', 0),
                    themes=social_data.get('themes', []),
                    sources=social_data.get('sources', {}),
                    confidence=social_data.get('confidence', 50.0),
                    timestamp=datetime.now()
                )
                
                return grok_analysis, social_packet
                
        except Exception as e:
            logger.error(f"Error in Grok scout phase: {e}")
            return None, None
    
    async def _deepseek_handoff_phase(self, symbol: str, all_data: Dict[str, Any], 
                                    social_packet: SocialDataPacket) -> Tuple[Optional[DeepSeekNewsAnalysis], Optional[DeepSeekSentimentAnalysis]]:
        """Phase 2: DeepSeek handoff processing for news and social refinement."""
        try:
            async with self.deepseek_service as deepseek:
                # Analyze news sentiment
                news_analysis = await deepseek.analyze_news_sentiment(symbol, all_data.get('news', {}))
                
                # Refine social sentiment from Grok's data packet
                grok_social_packet = {
                    'raw_sentiment': social_packet.raw_sentiment,
                    'mention_count': social_packet.mention_count,
                    'themes': social_packet.themes,
                    'sources': social_packet.sources,
                    'confidence': social_packet.confidence
                }
                refined_social = await deepseek.refine_social_sentiment(symbol, grok_social_packet)
                
                return news_analysis, refined_social
                
        except Exception as e:
            logger.error(f"Error in DeepSeek handoff phase: {e}")
            return None, None
    
    async def _cross_review_phase(self, symbol: str, grok_analysis: GrokAnalysis,
                                news_analysis: DeepSeekNewsAnalysis, 
                                social_analysis: DeepSeekSentimentAnalysis) -> Dict[str, float]:
        """Phase 3: Cross-review for mutual AI validation."""
        try:
            adjustments = {
                'grok_technical_correlation': 0.0,
                'deepseek_narrative_consistency': 0.0,
                'social_news_bridge_bonus': 0.0
            }
            
            # Grok reviews DeepSeek's sentiment with technical correlation
            technical_sentiment_correlation = self._calculate_technical_sentiment_correlation(
                grok_analysis, social_analysis
            )
            adjustments['grok_technical_correlation'] = technical_sentiment_correlation
            
            # DeepSeek reviews narrative consistency
            narrative_consistency = self._calculate_narrative_consistency(
                news_analysis, social_analysis
            )
            adjustments['deepseek_narrative_consistency'] = narrative_consistency
            
            # Social-news bridge scoring bonus
            if abs(social_analysis.social_news_bridge) > 0.5:  # Strong correlation
                adjustments['social_news_bridge_bonus'] = 0.05  # 5% bonus
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error in cross-review phase: {e}")
            return {}
    
    async def _consensus_resolution_phase(self, symbol: str, grok_analysis: GrokAnalysis,
                                        news_analysis: DeepSeekNewsAnalysis,
                                        social_analysis: DeepSeekSentimentAnalysis,
                                        cross_review_adjustments: Dict[str, float]) -> ConsensusResult:
        """Phase 4: Consensus resolution with agreement detection."""
        try:
            # Convert DeepSeek sentiment to confidence-like score for comparison
            deepseek_confidence = (social_analysis.sentiment_score + 1.0) * 50  # -1 to +1 → 0 to 100
            
            # Calculate agreement level
            confidence_diff = abs(grok_analysis.confidence - deepseek_confidence)
            if confidence_diff <= self.strong_agreement_threshold * 100:  # Convert to 0-100 scale
                agreement_level = AgreementLevel.STRONG_AGREEMENT
                confidence_adjustment = self.agreement_boost
            elif confidence_diff <= self.partial_agreement_threshold * 100:
                agreement_level = AgreementLevel.PARTIAL_AGREEMENT
                confidence_adjustment = 0.0  # No adjustment
            else:
                agreement_level = AgreementLevel.STRONG_DISAGREEMENT
                confidence_adjustment = -self.disagreement_penalty
            
            # Apply cross-review adjustments
            total_adjustment = confidence_adjustment + sum(cross_review_adjustments.values())
            
            # Calculate weighted consensus confidence
            technical_component = grok_analysis.confidence * 0.45  # 45% technical
            sentiment_component = deepseek_confidence * 0.35      # 35% sentiment
            fundamental_component = news_analysis.confidence * 0.20  # 20% fundamental
            
            base_consensus = technical_component + sentiment_component + fundamental_component
            final_confidence = max(0, min(100, base_consensus * (1 + total_adjustment)))
            
            # Determine final recommendation based on weighted analysis
            final_recommendation = self._determine_final_recommendation(
                grok_analysis, news_analysis, social_analysis, agreement_level
            )
            
            # Combine reasoning
            combined_reasoning = self._combine_reasoning(grok_analysis, news_analysis, social_analysis)
            
            return ConsensusResult(
                final_recommendation=final_recommendation,
                consensus_confidence=final_confidence,
                agreement_level=agreement_level,
                grok_score=grok_analysis.confidence,
                deepseek_score=deepseek_confidence,
                confidence_adjustment=total_adjustment,
                reasoning=combined_reasoning,
                risk_warning=grok_analysis.risk_warning,
                social_news_bridge=social_analysis.social_news_bridge,
                hybrid_validation_triggered=False
            )
            
        except Exception as e:
            logger.error(f"Error in consensus resolution: {e}")
            # Return default HOLD recommendation on error
            return ConsensusResult(
                final_recommendation="HOLD",
                consensus_confidence=50.0,
                agreement_level=AgreementLevel.STRONG_DISAGREEMENT,
                grok_score=0.0,
                deepseek_score=0.0,
                confidence_adjustment=0.0,
                reasoning="Error in consensus analysis - defaulting to HOLD",
                risk_warning="Analysis error - exercise extreme caution",
                social_news_bridge=0.0,
                hybrid_validation_triggered=False
            )

    async def _hybrid_validation_phase(self, symbol: str, consensus_result: ConsensusResult,
                                     all_data: Dict[str, Any]) -> ConsensusResult:
        """Phase 5: Hybrid validation using Reddit/Twitter as sanity checks."""
        try:
            # Get existing Reddit/Twitter validation data
            social_data = all_data.get('social', {})
            validation_sentiment = social_data.get('validation_sentiment', 0.0)  # From existing analyzers

            # Convert consensus to comparable sentiment score
            consensus_sentiment = (consensus_result.consensus_confidence - 50) / 50  # 0-100 → -1 to +1

            # Check for significant variance (>0.2 threshold)
            variance = abs(consensus_sentiment - validation_sentiment)

            if variance > self.validation_variance_threshold:
                logger.warning(f"Hybrid validation triggered for {symbol}: "
                              f"consensus={consensus_sentiment:.2f}, validation={validation_sentiment:.2f}")

                # Apply confidence penalty (10-15% reduction)
                penalty = min(0.15, variance * 0.3)  # Scale penalty with variance
                adjusted_confidence = consensus_result.consensus_confidence * (1 - penalty)

                # Update result
                consensus_result.consensus_confidence = max(0, adjusted_confidence)
                consensus_result.confidence_adjustment += -penalty
                consensus_result.hybrid_validation_triggered = True
                consensus_result.risk_warning = (consensus_result.risk_warning or "") + \
                    f" [VALIDATION ALERT: Social sentiment variance detected]"

            return consensus_result

        except Exception as e:
            logger.error(f"Error in hybrid validation: {e}")
            return consensus_result

    def _calculate_technical_sentiment_correlation(self, grok_analysis: GrokAnalysis,
                                                 social_analysis: DeepSeekSentimentAnalysis) -> float:
        """Calculate correlation between technical analysis and social sentiment."""
        try:
            # Convert Grok confidence to sentiment-like score
            grok_sentiment = (grok_analysis.confidence - 50) / 50  # 0-100 → -1 to +1

            # Calculate correlation (simple approach)
            correlation = 1 - abs(grok_sentiment - social_analysis.sentiment_score) / 2

            # Return small adjustment based on correlation
            if correlation > 0.8:
                return 0.03  # 3% bonus for high correlation
            elif correlation < 0.3:
                return -0.02  # 2% penalty for low correlation
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating technical-sentiment correlation: {e}")
            return 0.0

    def _calculate_narrative_consistency(self, news_analysis: DeepSeekNewsAnalysis,
                                       social_analysis: DeepSeekSentimentAnalysis) -> float:
        """Calculate consistency between news and social narratives."""
        try:
            # Simple consistency check based on sentiment alignment
            news_sentiment = news_analysis.sentiment_score
            social_sentiment = social_analysis.sentiment_score

            consistency = 1 - abs(news_sentiment - social_sentiment) / 2

            # Return small adjustment based on consistency
            if consistency > 0.8:
                return 0.02  # 2% bonus for high consistency
            elif consistency < 0.3:
                return -0.01  # 1% penalty for low consistency
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating narrative consistency: {e}")
            return 0.0

    def _determine_final_recommendation(self, grok_analysis: GrokAnalysis,
                                      news_analysis: DeepSeekNewsAnalysis,
                                      social_analysis: DeepSeekSentimentAnalysis,
                                      agreement_level: AgreementLevel) -> str:
        """Determine final recommendation based on all analyses."""
        try:
            # For strong disagreement, default to HOLD
            if agreement_level == AgreementLevel.STRONG_DISAGREEMENT:
                return "HOLD"

            # Weight the recommendations
            grok_weight = 0.6  # Technical analysis gets higher weight
            sentiment_weight = 0.4  # Combined sentiment weight

            # Convert Grok recommendation to numeric score
            grok_score = {"BUY": 1, "HOLD": 0, "SELL": -1}.get(grok_analysis.recommendation, 0)

            # Convert sentiment scores to recommendation scores
            avg_sentiment = (news_analysis.sentiment_score + social_analysis.sentiment_score) / 2
            sentiment_score = 1 if avg_sentiment > 0.2 else (-1 if avg_sentiment < -0.2 else 0)

            # Calculate weighted final score
            final_score = (grok_score * grok_weight) + (sentiment_score * sentiment_weight)

            # Convert back to recommendation
            if final_score > 0.3:
                return "BUY"
            elif final_score < -0.3:
                return "SELL"
            else:
                return "HOLD"

        except Exception as e:
            logger.error(f"Error determining final recommendation: {e}")
            return "HOLD"

    def _combine_reasoning(self, grok_analysis: GrokAnalysis,
                          news_analysis: DeepSeekNewsAnalysis,
                          social_analysis: DeepSeekSentimentAnalysis) -> str:
        """Combine reasoning from all AI analyses."""
        try:
            combined = f"TECHNICAL: {grok_analysis.reasoning[:200]}... " if grok_analysis.reasoning else ""
            combined += f"NEWS: {news_analysis.fundamental_impact} impact from {len(news_analysis.key_events)} events. "
            combined += f"SOCIAL: {social_analysis.crowd_psychology} psychology, {social_analysis.narrative[:100]}..."

            return combined[:500]  # Limit length

        except Exception as e:
            logger.error(f"Error combining reasoning: {e}")
            return "Combined analysis from dual AI system"
