"""
Unit tests for AI Consensus Engine.
Tests consensus workflow, agreement thresholds, and confidence adjustments.
Part of Priority A: Production Testing & Validation (Incremental Approach).
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.ai_consensus import (
    AIConsensusEngine, 
    ConsensusResult, 
    AgreementLevel, 
    SocialDataPacket
)
from app.services.grok_ai import GrokAnalysis
from app.services.deepseek_ai import DeepSeekSentimentAnalysis, DeepSeekNewsAnalysis


class TestAIConsensusEngine:
    """Test suite for AI Consensus Engine core functionality."""
    
    @pytest.fixture
    def mock_consensus_engine(self):
        """Create a consensus engine with mocked dependencies."""
        with patch('app.services.ai_consensus.get_redis_client'):
            engine = AIConsensusEngine()
            return engine
    
    @pytest.fixture
    def mock_all_data(self):
        """Mock comprehensive market data for testing."""
        return {
            'technical': {'rsi': 65, 'macd': 'bullish', 'price': 450.0},
            'news': {'sentiment': 0.6, 'headlines': ['NVDA beats earnings']},
            'social': {'sentiment_score': 0.7, 'mention_count': 150},
            'polymarket': [],
            'catalysts': {'catalysts': []},
            'volume': {'unusual_activity': True},
            'options_flow': {'call_put_ratio': 1.8}
        }
    
    @pytest.fixture
    def mock_grok_analysis(self):
        """Mock Grok analysis result."""
        return GrokAnalysis(
            recommendation='BUY_CALL',
            confidence=75.0,
            reasoning='Strong technical indicators',
            strike_price=460.0,
            expiration='2024-11-15',
            risk_level='MEDIUM',
            target_profit=25.0,
            max_loss=15.0,
            key_factors=['RSI oversold', 'earnings beat']
        )
    
    @pytest.fixture
    def mock_social_packet(self):
        """Mock social data packet from Grok."""
        return SocialDataPacket(
            raw_sentiment=0.7,
            mention_count=150,
            themes=['earnings beat', 'AI hype'],
            sources=['reddit', 'twitter'],
            confidence=0.8,
            data_quality='HIGH',
            timestamp='2024-10-27T10:30:00Z'
        )
    
    @pytest.fixture
    def mock_deepseek_news(self):
        """Mock DeepSeek news analysis."""
        return DeepSeekNewsAnalysis(
            sentiment_score=0.8,
            confidence=85,
            narrative='Strong positive earnings news',
            key_themes=['earnings', 'growth'],
            market_impact='BULLISH',
            urgency='HIGH'
        )
    
    @pytest.fixture
    def mock_deepseek_social(self):
        """Mock DeepSeek social sentiment analysis."""
        return DeepSeekSentimentAnalysis(
            sentiment_score=0.75,
            confidence=80,
            narrative='Bullish social sentiment with FOMO',
            key_themes=['earnings beat', 'AI momentum'],
            crowd_psychology='FOMO',
            sarcasm_detected=False,
            social_news_bridge=0.8
        )
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, mock_consensus_engine):
        """Test consensus engine initialization."""
        engine = mock_consensus_engine
        assert engine.strong_agreement_threshold == 0.2
        assert engine.partial_agreement_threshold == 0.5
        assert engine.agreement_boost == 0.12  # 12% boost
        assert engine.disagreement_penalty == 0.15  # 15% penalty
        assert engine.validation_variance_threshold == 0.2
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_consensus_engine):
        """Test async context manager functionality."""
        engine = mock_consensus_engine
        
        with patch('app.services.ai_consensus.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            async with engine as ctx_engine:
                assert ctx_engine is engine
                assert engine.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_strong_agreement_scenario(self, mock_consensus_engine, mock_all_data):
        """Test consensus with strong agreement between AIs (±0.2 difference)."""
        engine = mock_consensus_engine
        
        # Mock AI services to return similar scores
        with patch.object(engine, '_grok_scout_phase') as mock_grok, \
             patch.object(engine, '_deepseek_handoff_phase') as mock_deepseek, \
             patch.object(engine, '_cross_review_phase') as mock_cross_review, \
             patch.object(engine, '_hybrid_validation_phase') as mock_validation:
            
            # Setup mock returns - strong agreement (0.75 vs 0.8 = 0.05 difference)
            grok_analysis = GrokAnalysis(
                recommendation='BUY_CALL', confidence=75.0, reasoning='Technical bullish',
                risk_warning='Moderate risk', summary='Bullish outlook',
                key_factors=['RSI'], contrarian_view='Limited downside risk'
            )
            social_packet = SocialDataPacket(
                symbol='NVDA', raw_sentiment=0.75, mention_count=150, themes=['bullish'],
                sources={'reddit': 100, 'twitter': 50}, confidence=0.8,
                timestamp=datetime.fromisoformat('2024-10-27T10:30:00')
            )
            
            news_analysis = DeepSeekNewsAnalysis(
                sentiment_score=0.8, confidence=85, impact_assessment='HIGH',
                key_events=['earnings beat', 'strong guidance'], earnings_proximity=True,
                fundamental_impact='Strong positive earnings news with growth outlook'
            )
            social_analysis = DeepSeekSentimentAnalysis(
                sentiment_score=0.8, confidence=80, narrative='Bullish social',
                key_themes=['momentum'], crowd_psychology='FOMO',
                sarcasm_detected=False, social_news_bridge=0.8
            )
            
            mock_grok.return_value = (grok_analysis, social_packet)
            mock_deepseek.return_value = (news_analysis, social_analysis)
            mock_cross_review.return_value = {'technical_adjustment': 0.0, 'sentiment_adjustment': 0.0}
            
            # Mock final validation to return the consensus result
            expected_result = ConsensusResult(
                final_recommendation='BUY_CALL',
                consensus_confidence=85.0,  # Boosted by agreement
                agreement_level=AgreementLevel.STRONG_AGREEMENT,
                grok_score=75.0,
                deepseek_score=80.0,
                confidence_adjustment=0.12,  # 12% boost
                reasoning='Strong agreement between AIs with technical and sentiment alignment',
                risk_warning='Moderate risk',
                social_news_bridge=0.8,
                hybrid_validation_triggered=False
            )
            mock_validation.return_value = expected_result
            
            # Test the main workflow
            result = await engine.analyze_with_consensus('NVDA', mock_all_data, 75.0)
            
            # Assertions
            assert result is not None
            assert result.agreement_level == AgreementLevel.STRONG_AGREEMENT
            assert result.confidence_adjustment == 0.12
            assert result.consensus_confidence == 85.0
            assert result.final_recommendation == 'BUY_CALL'
    
    @pytest.mark.asyncio
    async def test_partial_agreement_scenario(self, mock_consensus_engine, mock_all_data):
        """Test consensus with partial agreement (0.2-0.5 difference)."""
        engine = mock_consensus_engine
        
        with patch.object(engine, '_grok_scout_phase') as mock_grok, \
             patch.object(engine, '_deepseek_handoff_phase') as mock_deepseek, \
             patch.object(engine, '_cross_review_phase') as mock_cross_review, \
             patch.object(engine, '_hybrid_validation_phase') as mock_validation:
            
            # Setup mock returns - partial agreement (0.6 vs 0.9 = 0.3 difference)
            grok_analysis = GrokAnalysis(
                recommendation='BUY_CALL', confidence=60.0, reasoning='Moderate technical',
                risk_warning='Moderate risk', summary='Mixed outlook',
                key_factors=['Mixed signals'], contrarian_view='Some uncertainty'
            )
            social_packet = SocialDataPacket(
                symbol='NVDA', raw_sentiment=0.6, mention_count=100, themes=['mixed'],
                sources={'reddit': 60, 'twitter': 40}, confidence=0.7,
                timestamp=datetime.fromisoformat('2024-10-27T10:30:00')
            )
            
            news_analysis = DeepSeekNewsAnalysis(
                sentiment_score=0.9, confidence=90, impact_assessment='HIGH',
                key_events=['product breakthrough', 'market expansion'], earnings_proximity=False,
                fundamental_impact='Major technological breakthrough with market implications'
            )
            social_analysis = DeepSeekSentimentAnalysis(
                sentiment_score=0.9, confidence=85, narrative='Strong bullish social',
                key_themes=['hype'], crowd_psychology='EUPHORIA',
                sarcasm_detected=False, social_news_bridge=0.9
            )
            
            mock_grok.return_value = (grok_analysis, social_packet)
            mock_deepseek.return_value = (news_analysis, social_analysis)
            mock_cross_review.return_value = {'technical_adjustment': 0.0, 'sentiment_adjustment': 0.0}
            
            expected_result = ConsensusResult(
                final_recommendation='BUY_CALL',
                consensus_confidence=75.0,  # Weighted average
                agreement_level=AgreementLevel.PARTIAL_AGREEMENT,
                grok_score=60.0,
                deepseek_score=90.0,
                confidence_adjustment=0.0,  # No boost/penalty for partial
                reasoning='Partial agreement - weighted by AI specialization',
                risk_warning='Moderate risk',
                social_news_bridge=0.9,
                hybrid_validation_triggered=False
            )
            mock_validation.return_value = expected_result
            
            result = await engine.analyze_with_consensus('NVDA', mock_all_data, 70.0)
            
            assert result is not None
            assert result.agreement_level == AgreementLevel.PARTIAL_AGREEMENT
            assert result.confidence_adjustment == 0.0
            assert result.consensus_confidence == 75.0
    
    @pytest.mark.asyncio
    async def test_strong_disagreement_scenario(self, mock_consensus_engine, mock_all_data):
        """Test consensus with strong disagreement (>0.5 difference)."""
        engine = mock_consensus_engine
        
        with patch.object(engine, '_grok_scout_phase') as mock_grok, \
             patch.object(engine, '_deepseek_handoff_phase') as mock_deepseek, \
             patch.object(engine, '_cross_review_phase') as mock_cross_review, \
             patch.object(engine, '_hybrid_validation_phase') as mock_validation:
            
            # Setup mock returns - strong disagreement (0.3 vs -0.4 = 0.7 difference)
            grok_analysis = GrokAnalysis(
                recommendation='BUY_CALL', confidence=30.0, reasoning='Weak technical',
                risk_warning='High risk', summary='Bearish outlook',
                key_factors=['Bearish indicators'], contrarian_view='Strong downside risk'
            )
            social_packet = SocialDataPacket(
                symbol='NVDA', raw_sentiment=0.3, mention_count=50, themes=['uncertainty'],
                sources={'reddit': 30, 'twitter': 20}, confidence=0.5,
                timestamp=datetime.fromisoformat('2024-10-27T10:30:00')
            )
            
            news_analysis = DeepSeekNewsAnalysis(
                sentiment_score=-0.4, confidence=80, impact_assessment='MEDIUM',
                key_events=['regulatory concerns', 'supply chain issues'], earnings_proximity=False,
                fundamental_impact='Regulatory headwinds and operational challenges'
            )
            social_analysis = DeepSeekSentimentAnalysis(
                sentiment_score=-0.4, confidence=75, narrative='Bearish social sentiment',
                key_themes=['fear'], crowd_psychology='FEAR',
                sarcasm_detected=True, social_news_bridge=-0.4
            )
            
            mock_grok.return_value = (grok_analysis, social_packet)
            mock_deepseek.return_value = (news_analysis, social_analysis)
            mock_cross_review.return_value = {'technical_adjustment': 0.0, 'sentiment_adjustment': 0.0}
            
            expected_result = ConsensusResult(
                final_recommendation='HOLD',  # Default for strong disagreement
                consensus_confidence=40.0,  # Penalized confidence
                agreement_level=AgreementLevel.STRONG_DISAGREEMENT,
                grok_score=30.0,
                deepseek_score=-40.0,
                confidence_adjustment=-0.15,  # 15% penalty
                reasoning='Strong disagreement between AIs - defaulting to HOLD with logged discrepancy',
                risk_warning='High risk',
                social_news_bridge=-0.4,
                hybrid_validation_triggered=True
            )
            mock_validation.return_value = expected_result
            
            result = await engine.analyze_with_consensus('NVDA', mock_all_data, 55.0)
            
            assert result is not None
            assert result.agreement_level == AgreementLevel.STRONG_DISAGREEMENT
            assert result.confidence_adjustment == -0.15
            assert result.final_recommendation == 'HOLD'
            assert result.consensus_confidence == 40.0
    
    @pytest.mark.asyncio
    async def test_grok_analysis_failure(self, mock_consensus_engine, mock_all_data):
        """Test handling when Grok analysis fails."""
        engine = mock_consensus_engine
        
        with patch.object(engine, '_grok_scout_phase') as mock_grok:
            mock_grok.return_value = (None, None)  # Simulate failure
            
            result = await engine.analyze_with_consensus('NVDA', mock_all_data, 75.0)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_deepseek_analysis_failure(self, mock_consensus_engine, mock_all_data):
        """Test handling when DeepSeek analysis fails."""
        engine = mock_consensus_engine
        
        with patch.object(engine, '_grok_scout_phase') as mock_grok, \
             patch.object(engine, '_deepseek_handoff_phase') as mock_deepseek:
            
            grok_analysis = GrokAnalysis(
                recommendation='BUY_CALL', confidence=75.0, reasoning='Technical',
                risk_warning='Moderate risk', summary='Technical outlook',
                key_factors=['RSI'], contrarian_view='Limited downside'
            )
            social_packet = SocialDataPacket(
                symbol='NVDA', raw_sentiment=0.7, mention_count=150, themes=['bullish'],
                sources={'reddit': 100, 'twitter': 50}, confidence=0.8,
                timestamp=datetime.fromisoformat('2024-10-27T10:30:00')
            )
            
            mock_grok.return_value = (grok_analysis, social_packet)
            mock_deepseek.return_value = (None, None)  # Simulate failure
            
            result = await engine.analyze_with_consensus('NVDA', mock_all_data, 75.0)
            
            assert result is None
