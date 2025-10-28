#!/usr/bin/env python3
"""
B1.1: Performance Logger Tests
Tests the ML performance logging system for dual AI analysis tracking
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.performance_logger import PerformanceLogger, PerformanceMetrics
from app.services.ai_consensus import ConsensusResult, AgreementLevel
from app.models.analysis_results import AnalysisResult
from app.core.database import get_db

class TestPerformanceLogger:
    """Test suite for ML performance logging system."""
    
    @pytest.fixture
    def mock_consensus_result(self):
        """Mock consensus result for testing."""
        return ConsensusResult(
            final_recommendation='BUY',
            consensus_confidence=82.5,
            agreement_level=AgreementLevel.STRONG_AGREEMENT,
            grok_score=80.0,
            deepseek_score=85.0,
            confidence_adjustment=0.12,
            reasoning='Strong bullish consensus from dual AI analysis',
            risk_warning='Monitor market volatility',
            social_news_bridge=0.75,
            hybrid_validation_triggered=False
        )
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        return mock_redis
    
    @pytest.mark.asyncio
    async def test_performance_metrics_creation(self, mock_consensus_result):
        """Test creation of performance metrics."""
        start_time = time.time()
        time.sleep(0.1)  # Simulate processing time

        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
                await logger.log_dual_ai_performance(
                    symbol="NVDA",
                    analysis_id=123,
                    consensus_result=mock_consensus_result,
                    start_time=start_time,
                    grok_start_time=start_time + 0.02,
                    deepseek_start_time=start_time + 0.05,
                    consensus_start_time=start_time + 0.08,
                    cache_hit=False,
                    api_calls_count=2,
                    data_sources=["alpha_vantage", "newsapi"],
                    ml_context={"vix": 18.5, "market_hours": True}
                )
            
            # Verify metrics were queued
            assert not logger.performance_queue.empty()
            
            # Get the queued metrics
            metrics = await logger.performance_queue.get()
            
            assert metrics.symbol == "NVDA"
            assert metrics.analysis_id == 123
            assert metrics.response_time_ms >= 100  # At least 100ms
            assert metrics.cache_hit == False
            assert metrics.ai_cost_cents == 3  # 2 + 1 for Grok + DeepSeek
            assert metrics.api_calls_count == 2
            assert metrics.data_sources_used == ["alpha_vantage", "newsapi"]
            assert metrics.performance_tier in ["fast", "standard", "slow"]
            assert metrics.consensus_score == 82.5
            assert metrics.agreement_level == "strong_agreement"
            assert metrics.confidence_adjustment == 0.12
            assert "vix" in metrics.ml_features
    
    @pytest.mark.asyncio
    async def test_performance_tier_classification(self, mock_consensus_result):
        """Test performance tier classification logic."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
            
                # Test fast tier (< 200ms)
                start_time = time.time()
                time.sleep(0.05)  # 50ms

                await logger.log_dual_ai_performance(
                    symbol="AAPL",
                    analysis_id=1,
                    consensus_result=mock_consensus_result,
                    start_time=start_time
                )

                metrics = await logger.performance_queue.get()
                assert metrics.performance_tier == "fast"

                # Test standard tier (200-500ms)
                start_time = time.time()
                time.sleep(0.3)  # 300ms

                await logger.log_dual_ai_performance(
                    symbol="TSLA",
                    analysis_id=2,
                    consensus_result=mock_consensus_result,
                    start_time=start_time
                )

                metrics = await logger.performance_queue.get()
                assert metrics.performance_tier == "standard"
    
    @pytest.mark.asyncio
    async def test_cache_hit_cost_calculation(self, mock_consensus_result):
        """Test cost calculation with cache hits."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
            
                # Test cache miss (full cost)
                await logger.log_dual_ai_performance(
                    symbol="MSFT",
                    analysis_id=1,
                    consensus_result=mock_consensus_result,
                    start_time=time.time(),
                    cache_hit=False
                )

                metrics = await logger.performance_queue.get()
                assert metrics.ai_cost_cents == 3  # 2 + 1 for Grok + DeepSeek

                # Test cache hit (no cost)
                await logger.log_dual_ai_performance(
                    symbol="GOOGL",
                    analysis_id=2,
                    consensus_result=mock_consensus_result,
                    start_time=time.time(),
                    cache_hit=True
                )

                metrics = await logger.performance_queue.get()
                assert metrics.ai_cost_cents == 0  # No cost for cache hit
    
    @pytest.mark.asyncio
    async def test_handoff_delta_calculation(self, mock_consensus_result):
        """Test handoff delta calculation between AI phases."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
            
                start_time = time.time()
                grok_start = start_time + 0.1
                deepseek_start = start_time + 0.3

                await logger.log_dual_ai_performance(
                    symbol="AMD",
                    analysis_id=1,
                    consensus_result=mock_consensus_result,
                    start_time=start_time,
                    grok_start_time=grok_start,
                    deepseek_start_time=deepseek_start
                )

                metrics = await logger.performance_queue.get()
                assert metrics.handoff_delta == pytest.approx(0.2, abs=0.01)  # 200ms delta
    
    @pytest.mark.asyncio
    async def test_redis_caching(self, mock_consensus_result, mock_redis_client):
        """Test Redis caching of performance metrics."""
        with patch('app.services.performance_logger.get_redis_client', return_value=mock_redis_client):
            async with PerformanceLogger() as logger:
            
                await logger.log_dual_ai_performance(
                    symbol="INTC",
                    analysis_id=123,
                    consensus_result=mock_consensus_result,
                    start_time=time.time()
                )

                # Verify Redis setex was called
                mock_redis_client.setex.assert_called_once()
                call_args = mock_redis_client.setex.call_args

                # Check cache key format
                cache_key = call_args[0][0]
                assert cache_key == "perf_metrics:INTC:123"

                # Check TTL (1 hour)
                ttl = call_args[0][1]
                assert ttl == 3600
    
    @pytest.mark.asyncio
    async def test_batch_processing_simulation(self, mock_consensus_result):
        """Test batch processing simulation (without actual DB writes)."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
            
                # Queue multiple metrics
                symbols = ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL"]
                for i, symbol in enumerate(symbols):
                    await logger.log_dual_ai_performance(
                        symbol=symbol,
                        analysis_id=i + 1,
                        consensus_result=mock_consensus_result,
                        start_time=time.time()
                    )

                # Verify all metrics were queued
                assert logger.performance_queue.qsize() == 5

                # Simulate batch processing
                batch = []
                while not logger.performance_queue.empty():
                    metrics = await logger.performance_queue.get()
                    batch.append(metrics)

                assert len(batch) == 5
                assert all(isinstance(m, PerformanceMetrics) for m in batch)
    
    @pytest.mark.asyncio
    async def test_performance_summary_structure(self):
        """Test performance summary data structure."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
                # Mock database response
                with patch('app.services.performance_logger.get_db') as mock_get_db:
                    mock_db = MagicMock()
                    mock_result = MagicMock()
                    mock_result.total_analyses = 100
                    mock_result.avg_response_time = 250.5
                    mock_result.min_response_time = 120
                    mock_result.max_response_time = 480
                    mock_result.total_cost_cents = 300
                    mock_result.avg_cost_per_analysis = 3.0
                    mock_result.cache_hits = 80
                    mock_result.cache_misses = 20
                    mock_result.strong_agreements = 60
                    mock_result.partial_agreements = 30
                    mock_result.strong_disagreements = 10
                    mock_result.fast_analyses = 25
                    mock_result.standard_analyses = 65
                    mock_result.slow_analyses = 10

                    mock_db.execute.return_value.fetchone.return_value = mock_result
                    mock_get_db.return_value = iter([mock_db])

                    summary = await logger.get_performance_summary(days=7)

                    # Verify summary structure
                    assert summary["total_analyses"] == 100
                    assert summary["avg_response_time_ms"] == 250.5
                    assert summary["cache_hit_rate"] == 80.0  # 80/(80+20) * 100
                    assert summary["total_cost_cents"] == 300

                    # Verify agreement distribution
                    agreement_dist = summary["agreement_distribution"]
                    assert agreement_dist["strong_agreement"] == 60
                    assert agreement_dist["partial_agreement"] == 30
                    assert agreement_dist["strong_disagreement"] == 10

                    # Verify performance distribution
                    perf_dist = summary["performance_distribution"]
                    assert perf_dist["fast"] == 25
                    assert perf_dist["standard"] == 65
                    assert perf_dist["slow"] == 10
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_consensus_result):
        """Test error handling in performance logging."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
                # Test with invalid Redis client
                logger.redis_client = None
            
                # Should not raise exception
                await logger.log_dual_ai_performance(
                    symbol="ERROR_TEST",
                    analysis_id=999,
                    consensus_result=mock_consensus_result,
                    start_time=time.time()
                )

                # Metrics should still be queued
                assert not logger.performance_queue.empty()

                metrics = await logger.performance_queue.get()
                assert metrics.symbol == "ERROR_TEST"
    
    def test_performance_metrics_dataclass(self):
        """Test PerformanceMetrics dataclass structure."""
        metrics = PerformanceMetrics(
            symbol="TEST",
            analysis_id=1,
            response_time_ms=250,
            cache_hit=True,
            ai_cost_cents=0,
            grok_analysis_time=datetime.now(),
            deepseek_analysis_time=datetime.now(),
            consensus_time=datetime.now(),
            handoff_delta=0.15,
            ml_features={"vix": 20.0},
            consensus_score=75.0,
            api_calls_count=2,
            data_sources_used=["demo"],
            performance_tier="standard",
            agreement_level="strong_agreement",
            confidence_adjustment=0.12
        )
        
        assert metrics.symbol == "TEST"
        assert metrics.response_time_ms == 250
        assert metrics.cache_hit == True
        assert metrics.performance_tier == "standard"
        assert "vix" in metrics.ml_features

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
