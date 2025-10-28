"""
Tests for Cost Monitor Service
Comprehensive testing of API usage tracking and cost estimation
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.cost_monitor import CostMonitor, APIService, APIUsage, APILimits, CostAlert


class TestCostMonitor:
    """Test suite for CostMonitor service."""
    
    @pytest.fixture
    async def cost_monitor(self):
        """Create a CostMonitor instance with mocked Redis."""
        with patch('app.services.cost_monitor.get_redis_client', return_value=AsyncMock()) as mock_redis:
            monitor = CostMonitor()
            monitor.redis_client = AsyncMock()  # Set mock Redis client directly
            return monitor
    
    @pytest.mark.asyncio
    async def test_api_limits_initialization(self, cost_monitor):
        """Test that API limits are properly initialized."""
        limits = cost_monitor.api_limits
        
        # Check that all services have limits defined
        assert len(limits) == len(APIService)
        
        # Check specific service limits
        assert limits[APIService.GROK].cost_per_request == 2.0
        assert limits[APIService.DEEPSEEK].cost_per_request == 1.0
        assert limits[APIService.ALPHA_VANTAGE].requests_per_day == 25
        assert limits[APIService.ALPHA_VANTAGE].requests_per_minute == 5
        assert limits[APIService.NEWSAPI].requests_per_day == 1000
        assert limits[APIService.REDDIT].requests_per_minute == 60
        assert limits[APIService.TWITTER].requests_per_month == 500000
    
    @pytest.mark.asyncio
    async def test_track_api_call_basic(self, cost_monitor):
        """Test basic API call tracking."""
        # Mock Redis get to return None (no existing data)
        cost_monitor.redis_client.get.return_value = None
        
        result = await cost_monitor.track_api_call(
            service=APIService.GROK,
            tokens_used=100
        )
        
        assert result['service'] == 'grok'
        assert result['usage']['requests_today'] == 1
        assert result['usage']['tokens_used'] == 100
        assert result['cost_today'] == 2.0  # 2¢ per request
        
        # Verify Redis operations
        cost_monitor.redis_client.get.assert_called_once()
        cost_monitor.redis_client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_api_call_with_tokens(self, cost_monitor):
        """Test API call tracking with token-based pricing."""
        cost_monitor.redis_client.get.return_value = None
        
        result = await cost_monitor.track_api_call(
            service=APIService.DEEPSEEK,
            tokens_used=500
        )
        
        # Should use token-based pricing: 500 tokens * 0.0001 * 100 = 5¢
        expected_cost = 500 * 0.0001 * 100
        assert result['cost_today'] == expected_cost
        assert result['usage']['tokens_used'] == 500
    
    @pytest.mark.asyncio
    async def test_track_api_call_with_existing_usage(self, cost_monitor):
        """Test API call tracking with existing usage data."""
        # Mock existing usage data
        existing_usage = APIUsage(
            service=APIService.GROK,
            requests_today=5,
            cost_today=10.0,
            tokens_used=250
        )
        
        usage_dict = {
            'service': 'grok',
            'requests_today': 5,
            'cost_today': 10.0,
            'tokens_used': 250,
            'requests_this_minute': 0,
            'requests_this_month': 5,
            'cost_this_month': 10.0,
            'last_request_time': None,
            'rate_limit_hit': False,
            'upgrade_recommended': False
        }
        
        cost_monitor.redis_client.get.return_value = json.dumps(usage_dict)
        
        result = await cost_monitor.track_api_call(
            service=APIService.GROK,
            tokens_used=100
        )
        
        # Should add to existing usage
        assert result['usage']['requests_today'] == 6
        assert result['usage']['tokens_used'] == 350
        assert result['cost_today'] == 12.0  # 10.0 + 2.0
    
    @pytest.mark.asyncio
    async def test_rate_limit_checking(self, cost_monitor):
        """Test rate limit checking logic."""
        # Create usage data that approaches rate limits
        usage_data = APIUsage(
            service=APIService.ALPHA_VANTAGE,
            requests_today=20,  # 80% of 25 daily limit
            requests_this_minute=4  # 80% of 5 minute limit
        )
        
        status = await cost_monitor._check_rate_limits(APIService.ALPHA_VANTAGE, usage_data)
        
        assert status['upgrade_recommended'] is True
        assert status['limit_hit'] is False
        assert status['utilization_percent'] == 80.0
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, cost_monitor):
        """Test rate limit exceeded detection."""
        usage_data = APIUsage(
            service=APIService.ALPHA_VANTAGE,
            requests_today=25,  # At daily limit
            requests_this_minute=5  # At minute limit
        )
        
        status = await cost_monitor._check_rate_limits(APIService.ALPHA_VANTAGE, usage_data)
        
        assert status['limit_hit'] is True
        assert status['utilization_percent'] == 100.0
    
    @pytest.mark.asyncio
    async def test_cost_alert_threshold(self, cost_monitor):
        """Test cost alert threshold checking."""
        # Set low threshold for testing
        cost_monitor.cost_alert.threshold_daily = 100.0  # $1.00
        
        await cost_monitor._check_cost_alerts(150.0, 500.0)  # $1.50 daily, $5.00 monthly
        
        assert cost_monitor.cost_alert.alert_triggered is True
        assert cost_monitor.cost_alert.last_alert_time is not None
        
        # Verify alert was sent to Redis
        cost_monitor.redis_client.lpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_usage_stats(self, cost_monitor):
        """Test getting comprehensive usage statistics."""
        # Mock Redis responses for different services
        def mock_get(key):
            if 'grok' in key:
                return json.dumps({
                    'service': 'grok',
                    'requests_today': 10,
                    'cost_today': 20.0,
                    'tokens_used': 1000,
                    'requests_this_minute': 2,
                    'requests_this_month': 50,
                    'cost_this_month': 100.0,
                    'last_request_time': None,
                    'rate_limit_hit': False,
                    'upgrade_recommended': False
                })
            elif 'deepseek' in key:
                return json.dumps({
                    'service': 'deepseek',
                    'requests_today': 5,
                    'cost_today': 5.0,
                    'tokens_used': 500,
                    'requests_this_minute': 1,
                    'requests_this_month': 25,
                    'cost_this_month': 25.0,
                    'last_request_time': None,
                    'rate_limit_hit': False,
                    'upgrade_recommended': False
                })
            return None
        
        cost_monitor.redis_client.get.side_effect = mock_get
        
        stats = await cost_monitor.get_all_usage_stats()
        
        assert 'services' in stats
        assert 'totals' in stats
        assert stats['totals']['cost_today'] == 25.0  # 20.0 + 5.0
        assert stats['totals']['cost_this_month'] == 125.0  # 100.0 + 25.0
        assert stats['totals']['cost_today_usd'] == 0.25
    
    @pytest.mark.asyncio
    async def test_cost_trends(self, cost_monitor):
        """Test cost trends calculation."""
        # Mock daily cost data
        def mock_get(key):
            if 'daily_cost:' in key:
                return '50.0'  # $0.50 per day
            return None
        
        cost_monitor.redis_client.get.side_effect = mock_get
        
        trends = await cost_monitor.get_cost_trends(7)
        
        assert 'daily_trends' in trends
        assert 'average_daily_cost' in trends
        assert 'projected_monthly_cost' in trends
        assert trends['average_daily_cost'] == 50.0
        assert trends['projected_monthly_cost'] == 1500.0  # 50.0 * 30
    
    @pytest.mark.asyncio
    async def test_reset_daily_counters(self, cost_monitor):
        """Test daily counter reset functionality."""
        # Mock existing usage data
        usage_dict = {
            'service': 'grok',
            'requests_today': 10,
            'cost_today': 20.0,
            'requests_this_minute': 2,
            'requests_this_month': 50,
            'cost_this_month': 100.0,
            'tokens_used': 1000,
            'last_request_time': None,
            'rate_limit_hit': False,
            'upgrade_recommended': False
        }
        
        cost_monitor.redis_client.get.return_value = json.dumps(usage_dict)
        
        await cost_monitor.reset_daily_counters()
        
        # Verify daily cost was stored
        cost_monitor.redis_client.setex.assert_called()
        
        # Verify usage data was updated (reset daily counters)
        # This would be verified by checking the setex call with updated data
        assert cost_monitor.cost_alert.alert_triggered is False
    
    @pytest.mark.asyncio
    async def test_upgrade_recommendations(self, cost_monitor):
        """Test upgrade recommendations generation."""
        # Mock usage data with upgrade recommendations
        usage_dict = {
            'service': 'alpha_vantage',
            'requests_today': 20,  # 80% of limit
            'requests_this_minute': 4,
            'requests_this_month': 500,
            'cost_today': 0.0,
            'cost_this_month': 0.0,
            'tokens_used': 0,
            'last_request_time': None,
            'rate_limit_hit': False,
            'upgrade_recommended': True
        }
        
        cost_monitor.redis_client.get.return_value = json.dumps(usage_dict)
        
        recommendations = await cost_monitor.get_upgrade_recommendations()
        
        assert len(recommendations) > 0
        assert recommendations[0]['service'] == 'alpha_vantage'
        assert 'recommendation' in recommendations[0]
        assert 'priority' in recommendations[0]
    
    @pytest.mark.asyncio
    async def test_error_handling(self, cost_monitor):
        """Test error handling in cost monitoring."""
        # Mock Redis error
        cost_monitor.redis_client.get.side_effect = Exception("Redis connection error")
        
        result = await cost_monitor.track_api_call(
            service=APIService.GROK,
            tokens_used=100
        )
        
        assert 'error' in result
        assert 'Redis connection error' in result['error']
    
    def test_upgrade_messages(self, cost_monitor):
        """Test upgrade recommendation messages."""
        message = cost_monitor._get_upgrade_message(APIService.ALPHA_VANTAGE)
        assert 'Alpha Vantage Premium' in message
        
        message = cost_monitor._get_upgrade_message(APIService.NEWSAPI)
        assert 'NewsAPI Commercial' in message
        
        message = cost_monitor._get_upgrade_message(APIService.GROK)
        assert 'optimizing prompts' in message
