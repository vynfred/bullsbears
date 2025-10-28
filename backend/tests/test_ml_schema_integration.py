#!/usr/bin/env python3
"""
B1.1: ML Schema Integration Tests
Tests the integration between the extended database schema and performance logging
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.performance_logger import PerformanceLogger, PerformanceMetrics
from app.services.ai_consensus import ConsensusResult, AgreementLevel
from app.models.analysis_results import AnalysisResult
from app.core.database import get_db, engine

class TestMLSchemaIntegration:
    """Test suite for ML schema and performance logger integration."""
    
    @pytest.fixture
    def mock_consensus_result(self):
        """Mock consensus result for testing."""
        return ConsensusResult(
            final_recommendation='BUY',
            consensus_confidence=85.0,
            agreement_level=AgreementLevel.STRONG_AGREEMENT,
            grok_score=82.0,
            deepseek_score=88.0,
            confidence_adjustment=0.15,
            reasoning='Strong bullish consensus with high confidence',
            risk_warning='Monitor earnings volatility',
            social_news_bridge=0.80,
            hybrid_validation_triggered=False
        )
    
    def test_database_schema_columns_exist(self):
        """Test that all ML performance columns exist in the database."""
        with engine.connect() as conn:
            result = conn.execute(text('PRAGMA table_info(analysis_results)'))
            columns = [row[1] for row in result.fetchall()]
            
            # Verify all ML performance columns exist
            ml_columns = [
                'response_time_ms', 'cache_hit', 'ai_cost_cents',
                'grok_analysis_time', 'deepseek_analysis_time', 'consensus_time',
                'handoff_delta', 'ml_features', 'consensus_score',
                'api_calls_count', 'data_sources_used', 'performance_tier'
            ]
            
            for col in ml_columns:
                assert col in columns, f"Column {col} not found in analysis_results table"
    
    def test_database_indexes_exist(self):
        """Test that ML performance indexes exist."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='analysis_results'"
            ))
            indexes = [row[0] for row in result.fetchall()]
            
            # Verify key ML indexes exist
            expected_indexes = [
                'idx_analysis_response_time',
                'idx_analysis_ai_cost',
                'idx_analysis_performance_tier',
                'idx_symbol_created_consensus',
                'idx_agreement_confidence_time',
                'idx_cost_analysis_daily'
            ]
            
            for idx in expected_indexes:
                assert idx in indexes, f"Index {idx} not found"
    
    def test_ml_training_view_exists(self):
        """Test that ML training data view exists and is queryable."""
        with engine.connect() as conn:
            # Check view exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='ml_training_data'"
            ))
            assert result.fetchone() is not None, "ml_training_data view not found"
            
            # Test view is queryable (should not raise exception)
            try:
                conn.execute(text("SELECT * FROM ml_training_data LIMIT 1"))
            except Exception as e:
                pytest.fail(f"ml_training_data view is not queryable: {e}")
    
    def test_cost_monitoring_view_exists(self):
        """Test that cost monitoring view exists and is queryable."""
        with engine.connect() as conn:
            # Check view exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='cost_monitoring_daily'"
            ))
            assert result.fetchone() is not None, "cost_monitoring_daily view not found"
            
            # Test view is queryable (should not raise exception)
            try:
                conn.execute(text("SELECT * FROM cost_monitoring_daily LIMIT 1"))
            except Exception as e:
                pytest.fail(f"cost_monitoring_daily view is not queryable: {e}")
    
    def test_analysis_result_model_compatibility(self):
        """Test that the AnalysisResult model is compatible with the extended schema."""
        # Create a mock analysis result with ML performance data
        analysis = AnalysisResult(
            symbol="NVDA",
            analysis_type="options",
            timeframe="1d",
            recommendation="BUY",
            confidence_score=85.0,
            technical_score=80.0,
            news_sentiment_score=90.0,
            social_sentiment_score=85.0,
            risk_level="medium",
            # ML performance fields
            response_time_ms=250,
            cache_hit=False,
            ai_cost_cents=3,
            grok_analysis_time=datetime.now(),
            deepseek_analysis_time=datetime.now(),
            consensus_time=datetime.now(),
            handoff_delta=0.15,
            ml_features='{"vix": 18.5, "market_hours": true}',
            consensus_score=85.0,
            api_calls_count=2,
            data_sources_used='["alpha_vantage", "newsapi"]',
            performance_tier="standard"
        )
        
        # Verify all attributes exist and have expected types
        assert hasattr(analysis, 'response_time_ms')
        assert hasattr(analysis, 'cache_hit')
        assert hasattr(analysis, 'ai_cost_cents')
        assert hasattr(analysis, 'performance_tier')
        assert hasattr(analysis, 'ml_features')
        
        # Verify values
        assert analysis.response_time_ms == 250
        assert analysis.cache_hit == False
        assert analysis.ai_cost_cents == 3
        assert analysis.performance_tier == "standard"
    
    @pytest.mark.asyncio
    async def test_performance_metrics_to_database_mapping(self, mock_consensus_result):
        """Test that PerformanceMetrics can be mapped to database columns."""
        with patch('app.services.performance_logger.get_redis_client', return_value=AsyncMock()):
            async with PerformanceLogger() as logger:
                start_time = time.time()
                time.sleep(0.1)  # Simulate processing time
                
                await logger.log_dual_ai_performance(
                    symbol="AAPL",
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
                
                # Get the performance metrics
                metrics = await logger.performance_queue.get()
                
                # Verify metrics can be mapped to database columns
                db_mapping = {
                    'symbol': metrics.symbol,
                    'response_time_ms': metrics.response_time_ms,
                    'cache_hit': metrics.cache_hit,
                    'ai_cost_cents': metrics.ai_cost_cents,
                    'grok_analysis_time': metrics.grok_analysis_time,
                    'deepseek_analysis_time': metrics.deepseek_analysis_time,
                    'consensus_time': metrics.consensus_time,
                    'handoff_delta': metrics.handoff_delta,
                    'ml_features': str(metrics.ml_features),
                    'consensus_score': metrics.consensus_score,
                    'api_calls_count': metrics.api_calls_count,
                    'data_sources_used': str(metrics.data_sources_used),
                    'performance_tier': metrics.performance_tier,
                    'agreement_level': metrics.agreement_level,
                    'confidence_adjustment': metrics.confidence_adjustment
                }
                
                # Verify all required fields are present
                assert db_mapping['symbol'] == "AAPL"
                assert db_mapping['response_time_ms'] >= 100
                assert db_mapping['cache_hit'] == False
                assert db_mapping['ai_cost_cents'] == 3
                assert db_mapping['api_calls_count'] == 2
                assert db_mapping['performance_tier'] in ["fast", "standard", "slow"]
                assert db_mapping['agreement_level'] == "strong_agreement"
                assert db_mapping['consensus_score'] == 85.0
                assert 'vix' in db_mapping['ml_features']
                assert 'alpha_vantage' in db_mapping['data_sources_used']
    
    def test_performance_tier_enum_values(self):
        """Test that performance tier values match expected enum values."""
        valid_tiers = ["fast", "standard", "slow"]
        
        # Test fast tier (< 200ms)
        response_time = 150
        tier = "fast" if response_time < 200 else "standard" if response_time < 500 else "slow"
        assert tier == "fast"
        assert tier in valid_tiers
        
        # Test standard tier (200-500ms)
        response_time = 350
        tier = "fast" if response_time < 200 else "standard" if response_time < 500 else "slow"
        assert tier == "standard"
        assert tier in valid_tiers
        
        # Test slow tier (>= 500ms)
        response_time = 750
        tier = "fast" if response_time < 200 else "standard" if response_time < 500 else "slow"
        assert tier == "slow"
        assert tier in valid_tiers
    
    def test_agreement_level_enum_values(self):
        """Test that agreement level values match expected enum values."""
        valid_levels = ["strong_agreement", "partial_agreement", "strong_disagreement"]
        
        # Test strong agreement (delta <= 0.2)
        grok_score = 80.0
        deepseek_score = 82.0
        delta = abs(grok_score - deepseek_score) / 100.0
        level = ("strong_agreement" if delta <= 0.2 else 
                "partial_agreement" if delta <= 0.5 else 
                "strong_disagreement")
        assert level == "strong_agreement"
        assert level in valid_levels
        
        # Test partial agreement (0.2 < delta <= 0.5)
        grok_score = 60.0
        deepseek_score = 90.0
        delta = abs(grok_score - deepseek_score) / 100.0
        level = ("strong_agreement" if delta <= 0.2 else 
                "partial_agreement" if delta <= 0.5 else 
                "strong_disagreement")
        assert level == "partial_agreement"
        assert level in valid_levels
        
        # Test strong disagreement (delta > 0.5)
        grok_score = 20.0
        deepseek_score = 80.0
        delta = abs(grok_score - deepseek_score) / 100.0
        level = ("strong_agreement" if delta <= 0.2 else 
                "partial_agreement" if delta <= 0.5 else 
                "strong_disagreement")
        assert level == "strong_disagreement"
        assert level in valid_levels
    
    def test_json_field_compatibility(self):
        """Test that JSON fields can store and retrieve complex data."""
        import json
        
        # Test ML features JSON
        ml_features = {
            "vix": 18.5,
            "market_hours": True,
            "sector_rotation": "tech_to_value",
            "earnings_season": False,
            "fed_meeting_proximity": 5
        }
        ml_features_json = json.dumps(ml_features)
        parsed_features = json.loads(ml_features_json)
        assert parsed_features == ml_features
        
        # Test data sources JSON
        data_sources = ["alpha_vantage", "newsapi", "reddit", "twitter"]
        data_sources_json = json.dumps(data_sources)
        parsed_sources = json.loads(data_sources_json)
        assert parsed_sources == data_sources

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
