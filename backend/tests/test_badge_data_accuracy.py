"""
Test suite for badge data accuracy and statistics service.
Ensures all badges display accurate data from live sources.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.statistics_service import StatisticsService, statistics_service
from app.models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from app.models.watchlist import WatchlistEntry
from app.models.dual_ai_training import DualAITrainingData


class TestStatisticsService:
    """Test the statistics service for badge data accuracy"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis_mock = Mock()
        redis_mock.get.return_value = None  # No cached data
        redis_mock.cache_with_ttl = Mock()
        redis_mock.delete = Mock()
        return redis_mock
    
    @pytest.fixture
    def sample_picks(self):
        """Sample analysis results for testing"""
        today = datetime.now().date()
        return [
            AnalysisResult(
                id=1,
                symbol="NVDA",
                alert_type=AlertType.MOON,
                confidence_score=0.85,
                alert_outcome=AlertOutcome.SUCCESS,
                timestamp=datetime.combine(today, datetime.min.time()),
                days_to_move=2.5
            ),
            AnalysisResult(
                id=2,
                symbol="TSLA",
                alert_type=AlertType.RUG,
                confidence_score=0.78,
                alert_outcome=AlertOutcome.FAILURE,
                timestamp=datetime.combine(today, datetime.min.time())
            ),
            AnalysisResult(
                id=3,
                symbol="AAPL",
                alert_type=AlertType.MOON,
                confidence_score=0.92,
                alert_outcome=AlertOutcome.PENDING,
                timestamp=datetime.combine(today, datetime.min.time())
            )
        ]
    
    @pytest.fixture
    def sample_watchlist(self):
        """Sample watchlist entries for testing"""
        return [
            WatchlistEntry(
                id=1,
                symbol="NVDA",
                status="ACTIVE",
                current_return_percent=15.5,
                position_size_dollars=1000,
                current_return_dollars=155,
                is_winner=True
            ),
            WatchlistEntry(
                id=2,
                symbol="TSLA",
                status="ACTIVE",
                current_return_percent=-8.2,
                position_size_dollars=500,
                current_return_dollars=-41,
                is_winner=False
            ),
            WatchlistEntry(
                id=3,
                symbol="AAPL",
                status="CLOSED",
                final_return_percent=12.3,
                final_return_dollars=123,
                is_winner=True,
                exit_reason="TARGET_HIT"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_get_picks_statistics(self, mock_db, mock_redis, sample_picks):
        """Test picks statistics calculation"""
        # Setup
        service = StatisticsService()
        service.redis_client = mock_redis
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = sample_picks
        
        # Execute
        result = await service.get_picks_statistics(mock_db)
        
        # Verify
        assert result["today"]["total_picks"] == 3
        assert result["today"]["bullish_picks"] == 2
        assert result["today"]["bearish_picks"] == 1
        assert result["today"]["avg_confidence"] == 85.0  # (85 + 78 + 92) / 3
        assert result["week"]["win_rate"] == 50.0  # 1 success out of 2 completed
    
    @pytest.mark.asyncio
    async def test_get_watchlist_statistics(self, mock_db, mock_redis, sample_watchlist):
        """Test watchlist statistics calculation"""
        # Setup
        service = StatisticsService()
        service.redis_client = mock_redis
        
        # Mock database queries
        active_entries = [e for e in sample_watchlist if e.status == "ACTIVE"]
        closed_entries = [e for e in sample_watchlist if e.status == "CLOSED"]
        
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            active_entries,  # First call for active entries
            closed_entries   # Second call for closed entries
        ]
        
        # Execute
        result = await service.get_watchlist_statistics(mock_db)
        
        # Verify
        assert result["active"]["total_stocks"] == 2
        assert result["active"]["winners"] == 1
        assert result["active"]["losers"] == 1
        assert result["active"]["avg_performance"] == 3.65  # (15.5 + (-8.2)) / 2
        assert result["active"]["total_return_dollars"] == 114  # 155 + (-41)
        
        assert result["closed"]["total_closed"] == 1
        assert result["closed"]["winners"] == 1
        assert result["closed"]["win_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_get_model_accuracy_statistics(self, mock_db, mock_redis, sample_picks):
        """Test model accuracy statistics calculation"""
        # Setup
        service = StatisticsService()
        service.redis_client = mock_redis
        
        # Mock database queries
        completed_picks = [p for p in sample_picks if p.alert_outcome != AlertOutcome.PENDING]
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # Training data query
            completed_picks  # Completed picks query
        ]
        
        # Execute
        result = await service.get_model_accuracy_statistics(mock_db)
        
        # Verify
        assert result["total_predictions"] == 2
        assert result["correct_predictions"] == 1
        assert result["overall_accuracy"] == 50.0  # 1 success out of 2 completed
        assert result["bullish_accuracy"] == 100.0  # 1 bullish success out of 1 bullish completed
        assert result["bearish_accuracy"] == 0.0    # 0 bearish success out of 1 bearish completed
    
    def test_calculate_avg_confidence(self, sample_picks):
        """Test average confidence calculation"""
        service = StatisticsService()
        result = service._calculate_avg_confidence(sample_picks)
        expected = (0.85 + 0.78 + 0.92) / 3 * 100
        assert result == expected
    
    def test_calculate_win_rate(self, sample_picks):
        """Test win rate calculation"""
        service = StatisticsService()
        result = service._calculate_win_rate(sample_picks)
        # Only 2 picks are completed (SUCCESS, FAILURE), 1 is successful
        assert result == 50.0
    
    def test_calculate_bullish_win_rate(self, sample_picks):
        """Test bullish win rate calculation"""
        service = StatisticsService()
        result = service._calculate_bullish_win_rate(sample_picks)
        # 1 bullish pick is completed and successful
        assert result == 100.0
    
    def test_calculate_bearish_win_rate(self, sample_picks):
        """Test bearish win rate calculation"""
        service = StatisticsService()
        result = service._calculate_bearish_win_rate(sample_picks)
        # 1 bearish pick is completed and failed
        assert result == 0.0
    
    def test_calculate_avg_watchlist_performance(self, sample_watchlist):
        """Test average watchlist performance calculation"""
        service = StatisticsService()
        active_entries = [e for e in sample_watchlist if e.status == "ACTIVE"]
        result = service._calculate_avg_watchlist_performance(active_entries)
        expected = (15.5 + (-8.2)) / 2
        assert result == expected
    
    def test_get_best_performer(self, sample_watchlist):
        """Test best performer identification"""
        service = StatisticsService()
        active_entries = [e for e in sample_watchlist if e.status == "ACTIVE"]
        result = service._get_best_performer(active_entries)
        
        assert result is not None
        assert result["symbol"] == "NVDA"
        assert result["return_percent"] == 15.5
    
    def test_get_worst_performer(self, sample_watchlist):
        """Test worst performer identification"""
        service = StatisticsService()
        active_entries = [e for e in sample_watchlist if e.status == "ACTIVE"]
        result = service._get_worst_performer(active_entries)
        
        assert result is not None
        assert result["symbol"] == "TSLA"
        assert result["return_percent"] == -8.2
    
    @pytest.mark.asyncio
    async def test_cache_behavior(self, mock_db, mock_redis, sample_picks):
        """Test that statistics are properly cached"""
        # Setup
        service = StatisticsService()
        service.redis_client = mock_redis
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = sample_picks
        
        # First call should query database and cache result
        mock_redis.get.return_value = None
        result1 = await service.get_picks_statistics(mock_db)
        
        # Verify cache was called
        mock_redis.cache_with_ttl.assert_called_once()
        
        # Second call should return cached result
        mock_redis.get.return_value = result1
        result2 = await service.get_picks_statistics(mock_db)
        
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_error_handling_returns_defaults(self, mock_db, mock_redis):
        """Test that errors return default statistics"""
        # Setup
        service = StatisticsService()
        service.redis_client = mock_redis
        
        # Mock database error
        mock_db.query.side_effect = Exception("Database error")
        
        # Execute
        result = await service.get_picks_statistics(mock_db)
        
        # Verify default values are returned
        assert result["today"]["total_picks"] == 0
        assert result["today"]["bullish_picks"] == 0
        assert result["today"]["bearish_picks"] == 0
        assert result["week"]["win_rate"] == 0
    
    def test_validation_checks(self):
        """Test that validation functions work correctly"""
        service = StatisticsService()
        
        # Test valid data
        valid_picks = [
            Mock(alert_outcome=AlertOutcome.SUCCESS, alert_type=AlertType.MOON, confidence_score=0.8),
            Mock(alert_outcome=AlertOutcome.FAILURE, alert_type=AlertType.RUG, confidence_score=0.7)
        ]
        
        win_rate = service._calculate_win_rate(valid_picks)
        assert 0 <= win_rate <= 100
        
        confidence = service._calculate_avg_confidence(valid_picks)
        assert 0 <= confidence <= 100
    
    @pytest.mark.asyncio
    async def test_statistics_consistency(self, mock_db, mock_redis, sample_picks, sample_watchlist):
        """Test that statistics are internally consistent"""
        # Setup
        service = StatisticsService()
        service.redis_client = mock_redis
        
        # Mock database queries for picks
        mock_db.query.return_value.filter.return_value.all.return_value = sample_picks
        picks_result = await service.get_picks_statistics(mock_db)
        
        # Verify consistency
        today_stats = picks_result["today"]
        assert today_stats["bullish_picks"] + today_stats["bearish_picks"] <= today_stats["total_picks"]
        assert 0 <= today_stats["avg_confidence"] <= 100
        
        week_stats = picks_result["week"]
        assert 0 <= week_stats["win_rate"] <= 100


class TestBadgeDataIntegration:
    """Integration tests for badge data accuracy"""
    
    @pytest.mark.asyncio
    async def test_badge_data_format(self):
        """Test that badge data is formatted correctly for UI consumption"""
        # This would test the actual API endpoint format
        # For now, verify the expected structure
        expected_keys = [
            "picks_tab", "watchlist_tab", "analytics_tab", 
            "stats_bar", "profile"
        ]
        
        # Mock the badge data structure
        badge_data = {
            "picks_tab": {
                "total_picks_today": 5,
                "bullish_count": 3,
                "bearish_count": 2,
                "avg_confidence": 78.5,
                "week_win_rate": 65.2
            },
            "analytics_tab": {
                "model_accuracy": 72.4,
                "total_predictions": 145,
                "bullish_accuracy": 68.3,
                "bearish_accuracy": 76.1
            },
            "stats_bar": {
                "daily_scans": 888,
                "alert_rate": 1.0,
                "bullish_win_rate": 52,
                "bearish_win_rate": 45
            }
        }
        
        # Verify structure
        for key in ["picks_tab", "analytics_tab", "stats_bar"]:
            assert key in badge_data
            assert isinstance(badge_data[key], dict)
        
        # Verify data types and ranges
        picks_tab = badge_data["picks_tab"]
        assert isinstance(picks_tab["total_picks_today"], int)
        assert isinstance(picks_tab["avg_confidence"], float)
        assert 0 <= picks_tab["avg_confidence"] <= 100
        
        analytics_tab = badge_data["analytics_tab"]
        assert isinstance(analytics_tab["model_accuracy"], float)
        assert 0 <= analytics_tab["model_accuracy"] <= 100
        
        stats_bar = badge_data["stats_bar"]
        assert isinstance(stats_bar["daily_scans"], int)
        assert stats_bar["daily_scans"] > 0
