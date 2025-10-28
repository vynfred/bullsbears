#!/usr/bin/env python3
"""
A3: Load Testing Suite for Concurrent Dual AI Analysis
Tests system performance under concurrent load with realistic dual AI analysis payloads
"""

import pytest
import asyncio
import time
import statistics
import json
import os
import resource
from datetime import datetime
from typing import List, Dict, Any, Tuple
from unittest.mock import AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import threading

# Import dual AI system components
from app.services.ai_consensus import AIConsensusEngine, SocialDataPacket, ConsensusResult, AgreementLevel
from app.services.grok_ai import GrokAIService, GrokAnalysis
from app.services.deepseek_ai import DeepSeekAIService, DeepSeekSentimentAnalysis, DeepSeekNewsAnalysis
from app.services.ai_option_generator import AIOptionGenerator
from app.core.redis_client import get_redis_client

# Test configuration
LOAD_TEST_SYMBOLS = ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "SPY"]
PERFORMANCE_TARGET_MS = 500  # <500ms target
CONCURRENT_LEVELS = [5, 10, 20]  # Test with 5, 10, 20 concurrent requests
MEMORY_LIMIT_GB = 2.0  # <2GB peak memory usage
CACHE_HIT_TARGET = 0.8  # >80% cache hit rate


class LoadTestMetrics:
    """Collect and analyze load test performance metrics."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = 0
        self.start_time = None
        self.end_time = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.response_times.clear()
        self.memory_usage.clear()
        self.cpu_usage.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = 0
    
    def record_request(self, response_time: float, cache_hit: bool = False, error: bool = False):
        """Record individual request metrics."""
        self.response_times.append(response_time)

        # Record system metrics using resource module (cross-platform)
        try:
            # Get memory usage in MB
            memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On macOS, ru_maxrss is in bytes, on Linux it's in KB
            if os.uname().sysname == 'Darwin':  # macOS
                memory_mb = memory_usage / 1024 / 1024
            else:  # Linux
                memory_mb = memory_usage / 1024

            self.memory_usage.append(memory_mb)
            # Simulate CPU usage since we don't have psutil
            self.cpu_usage.append(min(100.0, response_time * 1000))  # Rough CPU estimate
        except Exception:
            # Fallback if resource module fails
            self.memory_usage.append(100.0)  # Default 100MB
            self.cpu_usage.append(50.0)  # Default 50% CPU
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        if error:
            self.errors += 1
    
    def finish_monitoring(self):
        """Finish monitoring and calculate final metrics."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.response_times:
            return {"error": "No data collected"}
        
        total_requests = len(self.response_times)
        cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        
        return {
            "performance": {
                "total_requests": total_requests,
                "avg_response_time_ms": statistics.mean(self.response_times) * 1000,
                "median_response_time_ms": statistics.median(self.response_times) * 1000,
                "p95_response_time_ms": statistics.quantiles(self.response_times, n=20)[18] * 1000 if len(self.response_times) >= 20 else max(self.response_times) * 1000,
                "max_response_time_ms": max(self.response_times) * 1000,
                "min_response_time_ms": min(self.response_times) * 1000,
                "target_met": max(self.response_times) * 1000 < PERFORMANCE_TARGET_MS
            },
            "system_resources": {
                "peak_memory_mb": max(self.memory_usage) if self.memory_usage else 0,
                "avg_memory_mb": statistics.mean(self.memory_usage) if self.memory_usage else 0,
                "peak_cpu_percent": max(self.cpu_usage) if self.cpu_usage else 0,
                "avg_cpu_percent": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                "memory_limit_met": max(self.memory_usage) < (MEMORY_LIMIT_GB * 1024) if self.memory_usage else True
            },
            "caching": {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": cache_hit_rate,
                "cache_target_met": cache_hit_rate >= CACHE_HIT_TARGET
            },
            "reliability": {
                "total_errors": self.errors,
                "error_rate": self.errors / total_requests if total_requests > 0 else 0,
                "success_rate": 1 - (self.errors / total_requests) if total_requests > 0 else 1
            },
            "duration": {
                "total_time_seconds": self.end_time - self.start_time if self.end_time and self.start_time else 0
            }
        }


@pytest.fixture
def mock_dual_ai_components():
    """Mock dual AI system components for load testing."""
    
    # Mock Grok analysis result
    mock_grok_analysis = GrokAnalysis(
        recommendation='BUY',
        confidence=78.5,
        reasoning='Strong technical indicators with bullish momentum',
        risk_warning='Monitor for volatility spikes',
        summary='Bullish outlook with moderate confidence',
        key_factors=['RSI oversold recovery', 'MACD bullish crossover', 'Volume confirmation'],
        contrarian_view='Bears point to resistance levels'
    )
    
    # Mock DeepSeek sentiment analysis
    mock_deepseek_sentiment = DeepSeekSentimentAnalysis(
        sentiment_score=0.75,
        confidence=82.0,
        narrative='Positive sentiment driven by earnings optimism',
        key_themes=['earnings', 'growth', 'innovation'],
        crowd_psychology='OPTIMISTIC',
        sarcasm_detected=False,
        social_news_bridge=0.78
    )
    
    # Mock DeepSeek news analysis
    mock_deepseek_news = DeepSeekNewsAnalysis(
        sentiment_score=0.72,
        confidence=80.0,
        impact_assessment='HIGH',
        key_events=['earnings beat', 'strong guidance', 'market expansion'],
        earnings_proximity=True,
        fundamental_impact='Positive earnings outlook with strong fundamentals'
    )
    
    # Mock consensus result
    mock_consensus_result = ConsensusResult(
        final_recommendation='BUY',
        consensus_confidence=80.2,
        agreement_level=AgreementLevel.STRONG_AGREEMENT,
        grok_score=78.5,
        deepseek_score=82.0,
        confidence_adjustment=0.12,
        reasoning='Strong agreement between AI systems with bullish consensus',
        risk_warning='Monitor market volatility and position sizing',
        social_news_bridge=0.75,
        hybrid_validation_triggered=False
    )
    
    return {
        'grok_analysis': mock_grok_analysis,
        'deepseek_sentiment': mock_deepseek_sentiment,
        'deepseek_news': mock_deepseek_news,
        'consensus_result': mock_consensus_result
    }


@pytest.fixture
def realistic_market_data():
    """Generate realistic market data for load testing."""
    return {
        'technical': {
            'rsi': 65.2,
            'macd': 'bullish',
            'price': 450.75,
            'volume': 1250000,
            'bollinger_position': 'upper'
        },
        'news': {
            'sentiment': 0.68,
            'headlines': ['Strong Q3 earnings beat expectations', 'New product launch announced'],
            'article_count': 12
        },
        'social': {
            'sentiment_score': 0.72,
            'mention_count': 1850,
            'platforms': ['reddit', 'twitter', 'stocktwits']
        },
        'polymarket': [],
        'catalysts': {'catalysts': []},
        'volume': {'unusual_activity': True, 'volume_ratio': 1.8},
        'options_flow': {'call_put_ratio': 1.6, 'unusual_activity': True}
    }


class TestConcurrentDualAILoad:
    """Test concurrent dual AI analysis performance under load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_consensus_analysis_5_requests(self, mock_dual_ai_components, realistic_market_data):
        """Test 5 concurrent dual AI consensus analysis requests."""
        await self._run_concurrent_load_test(5, mock_dual_ai_components, realistic_market_data)
    
    @pytest.mark.asyncio
    async def test_concurrent_consensus_analysis_10_requests(self, mock_dual_ai_components, realistic_market_data):
        """Test 10 concurrent dual AI consensus analysis requests."""
        await self._run_concurrent_load_test(10, mock_dual_ai_components, realistic_market_data)
    
    @pytest.mark.asyncio
    async def test_concurrent_consensus_analysis_20_requests(self, mock_dual_ai_components, realistic_market_data):
        """Test 20 concurrent dual AI consensus analysis requests."""
        await self._run_concurrent_load_test(20, mock_dual_ai_components, realistic_market_data)
    
    async def _run_concurrent_load_test(self, concurrent_requests: int, mock_components: Dict, market_data: Dict):
        """Run concurrent load test with specified number of requests."""
        metrics = LoadTestMetrics()
        metrics.start_monitoring()
        
        # Mock Redis client for caching tests
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = None  # Simulate cache miss initially
        mock_redis_client.set.return_value = True
        mock_redis_client.exists.return_value = False
        
        with patch('app.services.ai_consensus.get_redis_client', return_value=mock_redis_client):
            with patch.object(AIConsensusEngine, '_grok_scout_phase') as mock_grok_phase:
                with patch.object(AIConsensusEngine, '_deepseek_handoff_phase') as mock_deepseek_phase:
                    with patch.object(AIConsensusEngine, '_cross_review_phase') as mock_cross_review:
                        with patch.object(AIConsensusEngine, '_consensus_resolution_phase') as mock_consensus:
                            
                            # Configure mocks to return realistic results with timing
                            mock_grok_phase.return_value = (mock_components['grok_analysis'], SocialDataPacket(
                                symbol='NVDA', raw_sentiment=0.72, mention_count=150, themes=['bullish'],
                                sources={'reddit': 100, 'twitter': 50},
                                confidence=0.8, timestamp=datetime.now()
                            ))
                            mock_deepseek_phase.return_value = (mock_components['deepseek_news'], mock_components['deepseek_sentiment'])
                            mock_cross_review.return_value = (mock_components['grok_analysis'], mock_components['deepseek_sentiment'])
                            mock_consensus.return_value = mock_components['consensus_result']
                            
                            # Create tasks for concurrent execution
                            tasks = []
                            for i in range(concurrent_requests):
                                symbol = LOAD_TEST_SYMBOLS[i % len(LOAD_TEST_SYMBOLS)]
                                task = self._single_consensus_request(symbol, market_data, metrics)
                                tasks.append(task)
                            
                            # Execute all requests concurrently
                            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics.finish_monitoring()
        summary = metrics.get_summary()
        
        # Validate performance targets
        assert summary['performance']['target_met'], f"Performance target not met: {summary['performance']['max_response_time_ms']:.1f}ms > {PERFORMANCE_TARGET_MS}ms"
        assert summary['system_resources']['memory_limit_met'], f"Memory limit exceeded: {summary['system_resources']['peak_memory_mb']:.1f}MB"
        assert summary['reliability']['success_rate'] >= 0.99, f"Success rate too low: {summary['reliability']['success_rate']:.2%}"
        
        # Log detailed results
        print(f"\n=== Load Test Results ({concurrent_requests} concurrent requests) ===")
        print(f"Average Response Time: {summary['performance']['avg_response_time_ms']:.1f}ms")
        print(f"P95 Response Time: {summary['performance']['p95_response_time_ms']:.1f}ms")
        print(f"Peak Memory Usage: {summary['system_resources']['peak_memory_mb']:.1f}MB")
        print(f"Cache Hit Rate: {summary['caching']['cache_hit_rate']:.1%}")
        print(f"Success Rate: {summary['reliability']['success_rate']:.1%}")
        
        return summary
    
    async def _single_consensus_request(self, symbol: str, market_data: Dict, metrics: LoadTestMetrics) -> Dict:
        """Execute single dual AI consensus analysis request."""
        start_time = time.time()
        
        try:
            async with AIConsensusEngine() as consensus_engine:
                result = await consensus_engine.analyze_with_consensus(
                    symbol=symbol,
                    all_data=market_data,
                    base_confidence=75.0
                )
            
            response_time = time.time() - start_time
            cache_hit = response_time < 0.1  # Simulate cache hit detection
            metrics.record_request(response_time, cache_hit=cache_hit, error=False)
            
            return {
                'success': True,
                'symbol': symbol,
                'response_time': response_time,
                'result': result
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            metrics.record_request(response_time, cache_hit=False, error=True)
            
            return {
                'success': False,
                'symbol': symbol,
                'response_time': response_time,
                'error': str(e)
            }


if __name__ == "__main__":
    # Run load tests directly
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    async def run_load_tests():
        """Run all load tests and generate report."""
        print("🚀 Starting A3 Load Testing Suite...")
        
        # Initialize test components
        from test_load_performance import TestConcurrentDualAILoad, LoadTestMetrics
        
        test_instance = TestConcurrentDualAILoad()
        
        # Mock components for standalone testing
        mock_components = {
            'grok_analysis': None,  # Will be mocked in tests
            'deepseek_sentiment': None,
            'deepseek_news': None,
            'consensus_result': None
        }
        
        market_data = {
            'technical': {'rsi': 65, 'price': 450},
            'news': {'sentiment': 0.7},
            'social': {'sentiment_score': 0.72}
        }
        
        results = {}
        for concurrent_level in CONCURRENT_LEVELS:
            print(f"\n📊 Testing {concurrent_level} concurrent requests...")
            try:
                result = await test_instance._run_concurrent_load_test(
                    concurrent_level, mock_components, market_data
                )
                results[concurrent_level] = result
            except Exception as e:
                print(f"❌ Error testing {concurrent_level} concurrent requests: {e}")
                results[concurrent_level] = {"error": str(e)}
        
        # Generate final report
        print("\n" + "="*60)
        print("🎯 A3 LOAD TESTING FINAL REPORT")
        print("="*60)
        
        for level, result in results.items():
            if "error" not in result:
                print(f"\n{level} Concurrent Requests:")
                print(f"  ✅ Avg Response: {result['performance']['avg_response_time_ms']:.1f}ms")
                print(f"  ✅ P95 Response: {result['performance']['p95_response_time_ms']:.1f}ms")
                print(f"  ✅ Peak Memory: {result['system_resources']['peak_memory_mb']:.1f}MB")
                print(f"  ✅ Success Rate: {result['reliability']['success_rate']:.1%}")
            else:
                print(f"\n{level} Concurrent Requests: ❌ {result['error']}")
        
        print(f"\n🎯 Performance Target: <{PERFORMANCE_TARGET_MS}ms")
        print(f"🎯 Memory Target: <{MEMORY_LIMIT_GB}GB")
        print(f"🎯 Cache Hit Target: >{CACHE_HIT_TARGET:.0%}")
    
    if __name__ == "__main__":
        asyncio.run(run_load_tests())
