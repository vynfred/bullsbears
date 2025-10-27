#!/usr/bin/env python3
"""
Production Integration Tests for Dual AI System
Tests complete workflow with real API keys and performance validation
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import our dual AI system components
from app.services.ai_consensus import AIConsensusEngine, SocialDataPacket, ConsensusResult
from app.services.grok_ai import GrokAIService
from app.services.deepseek_ai import DeepSeekAIService
from app.services.ai_option_generator import AIOptionGenerator
from app.core.config import settings
from app.core.redis_client import get_redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionDualAITester:
    """Comprehensive production testing for dual AI system"""
    
    def __init__(self):
        self.consensus_engine = AIConsensusEngine()
        self.grok_ai = GrokAIService()
        self.deepseek_ai = DeepSeekAIService()
        self.option_generator = AIOptionGenerator()
        self.test_results = {}
        
    async def setup_test_environment(self):
        """Setup test environment with Redis connection"""
        try:
            redis_client = await get_redis_client()
            logger.info("✅ Redis client connected successfully")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e} (continuing with tests)")
            return False
    
    def create_comprehensive_test_data(self) -> Dict[str, Any]:
        """Create comprehensive test data for NVDA analysis"""
        return {
            "symbol": "NVDA",
            "technical_data": {
                "price": 875.50,
                "rsi": 68.5,
                "macd": {"signal": "bullish", "histogram": 2.3},
                "bollinger_bands": {"position": "upper", "squeeze": False},
                "volume": 45000000,
                "avg_volume": 35000000,
                "support_levels": [850, 825, 800],
                "resistance_levels": [900, 925, 950]
            },
            "news_data": {
                "articles": [
                    {
                        "title": "NVIDIA Reports Record Q3 Earnings, AI Demand Surges",
                        "sentiment": 0.8,
                        "source": "Reuters",
                        "published": "2024-10-27T10:00:00Z"
                    },
                    {
                        "title": "NVIDIA Partners with Major Cloud Providers for AI Infrastructure",
                        "sentiment": 0.6,
                        "source": "TechCrunch", 
                        "published": "2024-10-27T08:30:00Z"
                    }
                ],
                "overall_sentiment": 0.7,
                "news_count": 15
            },
            "social_data": {
                "reddit_sentiment": 0.65,
                "twitter_sentiment": 0.72,
                "stocktwits_sentiment": 0.68,
                "mention_volume": 2500,
                "trending_topics": ["AI earnings", "data center demand", "GPU shortage"]
            },
            "polymarket_data": [
                {
                    "question": "Will NVDA close above $900 by end of week?",
                    "probability": 0.68,
                    "volume": 50000
                }
            ],
            "catalyst_data": {
                "earnings_date": "2024-11-20",
                "events": ["AI Summit presentation", "New GPU launch rumored"],
                "analyst_upgrades": 3,
                "analyst_downgrades": 0
            },
            "unusual_volume_data": {
                "call_volume": 125000,
                "put_volume": 45000,
                "call_put_ratio": 2.78,
                "unusual_activity": True
            },
            "options_flow_data": {
                "large_trades": [
                    {"strike": 900, "expiry": "2024-11-15", "type": "call", "volume": 5000},
                    {"strike": 850, "expiry": "2024-11-08", "type": "put", "volume": 2000}
                ],
                "flow_sentiment": "bullish",
                "gamma_exposure": 1250000000
            }
        }
    
    async def test_individual_ai_services(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test individual AI services with performance timing"""
        results = {}

        # Test Grok AI Service
        logger.info("🤖 Testing Grok AI Service...")
        start_time = time.time()
        try:
            async with self.grok_ai as grok:
                grok_result = await grok.analyze_option_play(
                    symbol=test_data["symbol"],
                    technical_data=test_data["technical_data"],
                    news_data=test_data["news_data"],
                    social_data=test_data["social_data"],
                    polymarket_data=test_data["polymarket_data"],
                    catalyst_data=test_data["catalyst_data"],
                    unusual_volume_data=test_data["unusual_volume_data"],
                    options_flow_data=test_data["options_flow_data"],
                    confidence_score=0.75
                )
            grok_time = time.time() - start_time
            results["grok"] = {
                "success": True,
                "response_time": grok_time,
                "result": grok_result
            }
            logger.info(f"✅ Grok AI completed in {grok_time:.2f}s")
        except Exception as e:
            results["grok"] = {"success": False, "error": str(e)}
            logger.error(f"❌ Grok AI failed: {e}")

        # Test DeepSeek AI Service
        logger.info("🧠 Testing DeepSeek AI Service...")
        start_time = time.time()
        try:
            # Create Grok social packet format for DeepSeek
            grok_social_packet = {
                "reddit_sentiment": test_data["social_data"]["reddit_sentiment"],
                "twitter_sentiment": test_data["social_data"]["twitter_sentiment"],
                "mention_volume": test_data["social_data"]["mention_volume"],
                "trending_topics": test_data["social_data"]["trending_topics"],
                "confidence": 0.8,
                "raw_data": "80% of 2500 mentions bullish on NVDA due to AI earnings hype"
            }

            async with self.deepseek_ai as deepseek:
                deepseek_result = await deepseek.refine_social_sentiment(
                    symbol=test_data["symbol"],
                    grok_social_packet=grok_social_packet
                )
            deepseek_time = time.time() - start_time
            results["deepseek"] = {
                "success": True,
                "response_time": deepseek_time,
                "result": deepseek_result
            }
            logger.info(f"✅ DeepSeek AI completed in {deepseek_time:.2f}s")
        except Exception as e:
            results["deepseek"] = {"success": False, "error": str(e)}
            logger.error(f"❌ DeepSeek AI failed: {e}")

        return results
    
    async def test_consensus_engine_workflow(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test complete consensus engine workflow with performance timing"""
        logger.info("🎯 Testing Complete Consensus Engine Workflow...")
        start_time = time.time()

        try:
            # Prepare all_data parameter as expected by consensus engine
            all_data = {
                "technical_data": test_data["technical_data"],
                "news_data": test_data["news_data"],
                "social_data": test_data["social_data"],
                "polymarket_data": test_data["polymarket_data"],
                "catalyst_data": test_data["catalyst_data"],
                "unusual_volume_data": test_data["unusual_volume_data"],
                "options_flow_data": test_data["options_flow_data"]
            }

            consensus_result = await self.consensus_engine.analyze_with_consensus(
                symbol=test_data["symbol"],
                all_data=all_data,
                base_confidence=0.75
            )
            
            consensus_time = time.time() - start_time
            
            result = {
                "success": True,
                "response_time": consensus_time,
                "consensus_result": consensus_result,
                "performance_analysis": {
                    "meets_500ms_target": consensus_time < 0.5,
                    "recommendation": consensus_result.final_recommendation,
                    "confidence": consensus_result.consensus_confidence,
                    "agreement_level": consensus_result.agreement_level.value,
                    "grok_score": consensus_result.grok_score,
                    "deepseek_score": consensus_result.deepseek_score
                }
            }
            
            logger.info(f"✅ Consensus Engine completed in {consensus_time:.2f}s")
            logger.info(f"📊 Recommendation: {consensus_result.final_recommendation}")
            logger.info(f"📊 Confidence: {consensus_result.consensus_confidence:.1f}%")
            logger.info(f"📊 Agreement: {consensus_result.agreement_level.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Consensus Engine failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_option_generator_integration(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test AI Option Generator with dual AI integration"""
        logger.info("🎲 Testing AI Option Generator Integration...")
        start_time = time.time()

        try:
            option_plays = await self.option_generator.generate_option_plays(
                symbol=test_data["symbol"],
                max_plays=1
            )
            option_play = option_plays[0] if option_plays else None
            
            generation_time = time.time() - start_time
            
            if option_play:
                result = {
                    "success": True,
                    "response_time": generation_time,
                    "option_play": option_play,
                    "dual_ai_validation": {
                        "has_grok_score": option_play.grok_score is not None,
                        "has_deepseek_score": option_play.deepseek_score is not None,
                        "has_agreement_level": option_play.agreement_level is not None,
                        "has_confidence_adjustment": option_play.confidence_adjustment is not None,
                        "hybrid_validation_triggered": option_play.hybrid_validation_triggered
                    }
                }
            else:
                result = {"success": False, "error": "No option plays generated"}
            
            if option_play:
                logger.info(f"✅ Option Generator completed in {generation_time:.2f}s")
                logger.info(f"📊 Generated play: {option_play.recommendation}")
            else:
                logger.warning("⚠️ Option Generator completed but no plays generated")

            return result
            
        except Exception as e:
            logger.error(f"❌ Option Generator failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_comprehensive_tests(self):
        """Run all production tests and generate report"""
        logger.info("🚀 Starting Comprehensive Production Dual AI Tests...")
        logger.info("=" * 60)
        
        # Setup
        redis_available = await self.setup_test_environment()
        test_data = self.create_comprehensive_test_data()
        
        # Run tests
        individual_results = await self.test_individual_ai_services(test_data)
        consensus_results = await self.test_consensus_engine_workflow(test_data)
        generator_results = await self.test_option_generator_integration(test_data)
        
        # Compile results
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "redis_available": redis_available,
            "individual_ai_services": individual_results,
            "consensus_engine": consensus_results,
            "option_generator": generator_results,
            "summary": self.generate_test_summary(individual_results, consensus_results, generator_results)
        }
        
        self.print_test_report()
        return self.test_results
    
    def generate_test_summary(self, individual, consensus, generator) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = 0
        passed_tests = 0
        
        # Count individual service tests
        for service, result in individual.items():
            total_tests += 1
            if result.get("success", False):
                passed_tests += 1
        
        # Count consensus test
        total_tests += 1
        if consensus.get("success", False):
            passed_tests += 1
        
        # Count generator test
        total_tests += 1
        if generator.get("success", False):
            passed_tests += 1
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "performance_targets_met": {
                "consensus_under_500ms": consensus.get("performance_analysis", {}).get("meets_500ms_target", False)
            }
        }
    
    def print_test_report(self):
        """Print comprehensive test report"""
        logger.info("=" * 60)
        logger.info("📊 PRODUCTION DUAL AI TEST REPORT")
        logger.info("=" * 60)
        
        summary = self.test_results["summary"]
        logger.info(f"✅ Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
        logger.info(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        
        if self.test_results["consensus_engine"].get("success"):
            perf = self.test_results["consensus_engine"]["performance_analysis"]
            logger.info(f"⚡ Consensus Response Time: {self.test_results['consensus_engine']['response_time']:.2f}s")
            logger.info(f"🎯 <500ms Target Met: {'✅' if perf['meets_500ms_target'] else '❌'}")
        
        logger.info("=" * 60)
        logger.info("🎉 Production testing complete!")

async def main():
    """Main test execution"""
    tester = ProductionDualAITester()
    results = await tester.run_comprehensive_tests()
    
    # Save results to file
    with open("production_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("📁 Test results saved to production_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
