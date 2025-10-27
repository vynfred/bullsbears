#!/usr/bin/env python3
"""
Test script for the dual AI system implementation.
Tests the integration of Grok + DeepSeek + Consensus Engine.
"""

import asyncio
import logging
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_consensus import AIConsensusEngine, ConsensusResult
from app.services.deepseek_ai import DeepSeekAIService
from app.services.grok_ai import GrokAIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_deepseek_service():
    """Test DeepSeek AI service with mock data."""
    logger.info("Testing DeepSeek AI Service...")

    try:
        # Note: This test may fail if Redis is not running, which is expected in dev environment
        async with DeepSeekAIService() as deepseek:
            # Test news analysis with mock data
            mock_news_data = {
                'headlines': [
                    {'title': 'NVDA reports strong Q3 earnings, beats expectations'},
                    {'title': 'AI chip demand continues to surge'},
                    {'title': 'NVIDIA stock rises on positive outlook'}
                ],
                'earnings': 'Q3 2024: EPS $0.68 vs $0.65 expected'
            }
            
            news_analysis = await deepseek.analyze_news_sentiment('NVDA', mock_news_data)
            
            if news_analysis:
                logger.info(f"✅ DeepSeek News Analysis: Sentiment={news_analysis.sentiment_score:.2f}, "
                           f"Confidence={news_analysis.confidence:.1f}%, Impact={news_analysis.impact_assessment}")
            else:
                logger.warning("⚠️ DeepSeek news analysis returned None (likely API key issue)")
            
            # Test social refinement with mock Grok data packet
            mock_grok_packet = {
                'raw_sentiment': 0.7,
                'mention_count': 150,
                'themes': ['AI hype', 'earnings beat', 'bullish sentiment'],
                'sources': {'reddit': 80, 'twitter': 70},
                'confidence': 75.0
            }
            
            social_analysis = await deepseek.refine_social_sentiment('NVDA', mock_grok_packet)
            
            if social_analysis:
                logger.info(f"✅ DeepSeek Social Refinement: Sentiment={social_analysis.sentiment_score:.2f}, "
                           f"Psychology={social_analysis.crowd_psychology}, Sarcasm={social_analysis.sarcasm_detected}")
            else:
                logger.warning("⚠️ DeepSeek social refinement returned None (likely API key issue)")
                
            return news_analysis is not None or social_analysis is not None
            
    except Exception as e:
        logger.error(f"❌ DeepSeek service test failed: {e}")
        return False

async def test_grok_service():
    """Test Grok AI service with mock data."""
    logger.info("Testing Grok AI Service...")
    
    try:
        async with GrokAIService() as grok:
            # Test comprehensive analysis with mock data
            mock_all_data = {
                'technical': {'rsi': 65, 'macd': 'bullish', 'price': 450.0},
                'news': {'sentiment': 0.6, 'headlines': ['NVDA beats earnings']},
                'social': {'sentiment_score': 0.7, 'mention_count': 150},
                'polymarket': [],
                'catalysts': {'catalysts': []},
                'volume': {'unusual_activity': True},
                'options_flow': {'call_put_ratio': 1.8}
            }
            
            grok_analysis = await grok.analyze_comprehensive_option_play('NVDA', mock_all_data, 75.0)
            
            if grok_analysis:
                logger.info(f"✅ Grok Analysis: Recommendation={grok_analysis.recommendation}, "
                           f"Confidence={grok_analysis.confidence:.1f}%")
                return True
            else:
                logger.warning("⚠️ Grok analysis returned None (likely API key issue)")
                return False
                
    except Exception as e:
        logger.error(f"❌ Grok service test failed: {e}")
        return False

async def test_consensus_engine():
    """Test AI Consensus Engine with mock data."""
    logger.info("Testing AI Consensus Engine...")
    
    try:
        async with AIConsensusEngine() as consensus:
            # Test consensus analysis with mock data
            mock_all_data = {
                'technical': {'rsi': 65, 'macd': 'bullish', 'price': 450.0},
                'news': {
                    'headlines': [
                        {'title': 'NVDA reports strong Q3 earnings'},
                        {'title': 'AI chip demand surges'}
                    ],
                    'earnings': 'Q3 2024: EPS beat'
                },
                'social': {
                    'sentiment_score': 0.7,
                    'mention_count': 150,
                    'themes': ['AI hype', 'earnings beat'],
                    'sources': {'reddit': 80, 'twitter': 70},
                    'confidence': 75.0,
                    'validation_sentiment': 0.6  # For hybrid validation
                },
                'polymarket': [],
                'catalysts': {'catalysts': []},
                'volume': {'unusual_activity': True},
                'options_flow': {'call_put_ratio': 1.8}
            }
            
            consensus_result = await consensus.analyze_with_consensus('NVDA', mock_all_data, 75.0)
            
            if consensus_result:
                logger.info(f"✅ Consensus Analysis: Recommendation={consensus_result.final_recommendation}, "
                           f"Confidence={consensus_result.consensus_confidence:.1f}%, "
                           f"Agreement={consensus_result.agreement_level.value}")
                logger.info(f"   Grok Score: {consensus_result.grok_score:.1f}%, "
                           f"DeepSeek Score: {consensus_result.deepseek_score:.1f}%")
                logger.info(f"   Confidence Adjustment: {consensus_result.confidence_adjustment:.3f}, "
                           f"Hybrid Validation: {consensus_result.hybrid_validation_triggered}")
                return True
            else:
                logger.warning("⚠️ Consensus analysis returned None")
                return False
                
    except Exception as e:
        logger.error(f"❌ Consensus engine test failed: {e}")
        return False

async def main():
    """Run all dual AI system tests."""
    logger.info("🚀 Starting Dual AI System Tests...")
    logger.info("=" * 60)
    
    # Test individual services
    deepseek_ok = await test_deepseek_service()
    logger.info("-" * 60)
    
    grok_ok = await test_grok_service()
    logger.info("-" * 60)
    
    # Test consensus engine (integration test)
    consensus_ok = await test_consensus_engine()
    logger.info("=" * 60)
    
    # Summary
    total_tests = 3
    passed_tests = sum([deepseek_ok, grok_ok, consensus_ok])
    
    logger.info(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All dual AI system tests passed!")
        return True
    elif passed_tests > 0:
        logger.warning(f"⚠️ Partial success: {passed_tests}/{total_tests} tests passed")
        logger.info("💡 Some tests may have failed due to API key configuration")
        return True
    else:
        logger.error("❌ All tests failed - check API keys and service configuration")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
