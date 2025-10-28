"""
Tests for Cost Alerts Service
Testing alert generation, threshold monitoring, and notification management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.cost_alerts import CostAlertsService, Alert, AlertType, AlertSeverity
from app.services.cost_monitor import APIService


class TestCostAlertsService:
    """Test suite for CostAlertsService."""
    
    @pytest.fixture
    async def alerts_service(self):
        """Create a CostAlertsService instance with mocked dependencies."""
        with patch('app.services.cost_alerts.get_redis_client', return_value=AsyncMock()), \
             patch('app.services.cost_alerts.CostMonitor') as mock_monitor:
            
            # Mock cost monitor
            mock_monitor_instance = AsyncMock()
            mock_monitor.return_value = mock_monitor_instance
            mock_monitor_instance.__aenter__.return_value = mock_monitor_instance
            
            service = CostAlertsService()
            await service.__aenter__()
            yield service
            await service.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_alert_creation(self):
        """Test Alert dataclass creation and initialization."""
        alert = Alert(
            id="test_alert_1",
            type=AlertType.DAILY_THRESHOLD,
            severity=AlertSeverity.HIGH,
            message="Test alert message"
        )
        
        assert alert.id == "test_alert_1"
        assert alert.type == AlertType.DAILY_THRESHOLD
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Test alert message"
        assert alert.acknowledged is False
        assert alert.timestamp is not None
        assert alert.details == {}
    
    @pytest.mark.asyncio
    async def test_cost_threshold_alerts(self, alerts_service):
        """Test cost threshold alert generation."""
        # Mock usage stats with high costs
        mock_totals = {
            'cost_today': 600.0,  # $6.00 - exceeds critical threshold
            'cost_this_month': 12000.0  # $120.00 - exceeds critical threshold
        }
        
        alerts = await alerts_service._check_cost_thresholds(mock_totals)
        
        assert len(alerts) == 2  # Daily and monthly alerts
        
        # Check daily alert
        daily_alert = next(a for a in alerts if a.type == AlertType.DAILY_THRESHOLD)
        assert daily_alert.severity == AlertSeverity.CRITICAL
        assert "$6.00" in daily_alert.message
        assert daily_alert.details['cost_usd'] == 6.0
        
        # Check monthly alert
        monthly_alert = next(a for a in alerts if a.type == AlertType.MONTHLY_THRESHOLD)
        assert monthly_alert.severity == AlertSeverity.CRITICAL
        assert "$120.00" in monthly_alert.message
        assert monthly_alert.details['cost_usd'] == 120.0
    
    @pytest.mark.asyncio
    async def test_cost_warning_alerts(self, alerts_service):
        """Test cost warning alert generation."""
        # Mock usage stats with warning-level costs
        mock_totals = {
            'cost_today': 400.0,  # $4.00 - warning level
            'cost_this_month': 7000.0  # $70.00 - warning level
        }
        
        alerts = await alerts_service._check_cost_thresholds(mock_totals)
        
        assert len(alerts) == 2
        
        # Both should be warning level
        for alert in alerts:
            assert alert.severity == AlertSeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_rate_limit_alerts(self, alerts_service):
        """Test rate limit alert generation."""
        # Mock service data with rate limit hit
        service_data = {
            'rate_limit_hit': True,
            'requests_today': 25,
            'requests_this_minute': 5,
            'utilization_percent': 100.0
        }
        
        alerts = await alerts_service._check_rate_limit_alerts(
            APIService.ALPHA_VANTAGE, 
            service_data
        )
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.type == AlertType.RATE_LIMIT_HIT
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.service == APIService.ALPHA_VANTAGE
        assert "Rate limit hit" in alert.message
    
    @pytest.mark.asyncio
    async def test_upgrade_recommendation_alerts(self, alerts_service):
        """Test upgrade recommendation alert generation."""
        service_data = {
            'rate_limit_hit': False,
            'upgrade_recommended': True,
            'utilization_percent': 85.0
        }
        
        alerts = await alerts_service._check_rate_limit_alerts(
            APIService.NEWSAPI,
            service_data
        )
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.type == AlertType.UPGRADE_RECOMMENDED
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.service == APIService.NEWSAPI
        assert "Upgrade recommended" in alert.message
    
    @pytest.mark.asyncio
    async def test_check_all_alerts(self, alerts_service):
        """Test comprehensive alert checking."""
        # Mock usage stats
        mock_usage_stats = {
            'totals': {
                'cost_today': 600.0,  # Triggers critical alert
                'cost_this_month': 7000.0  # Triggers warning alert
            },
            'services': {
                'alpha_vantage': {
                    'rate_limit_hit': True,
                    'requests_today': 25,
                    'requests_this_minute': 5
                },
                'grok': {
                    'rate_limit_hit': False,
                    'upgrade_recommended': True,
                    'utilization_percent': 85.0
                }
            }
        }
        
        alerts_service.cost_monitor.get_all_usage_stats.return_value = mock_usage_stats
        
        alerts = await alerts_service.check_all_alerts()
        
        # Should have: 1 daily critical, 1 monthly warning, 1 rate limit hit, 1 upgrade recommendation
        assert len(alerts) >= 4
        
        # Verify Redis storage was called for each alert
        assert alerts_service.redis_client.setex.call_count >= 4
        assert alerts_service.redis_client.lpush.call_count >= 4
    
    @pytest.mark.asyncio
    async def test_store_alert(self, alerts_service):
        """Test alert storage in Redis."""
        alert = Alert(
            id="test_alert",
            type=AlertType.DAILY_THRESHOLD,
            severity=AlertSeverity.HIGH,
            service=APIService.GROK,
            message="Test alert"
        )
        
        await alerts_service._store_alert(alert)
        
        # Verify Redis operations
        alerts_service.redis_client.setex.assert_called_once()
        alerts_service.redis_client.lpush.assert_called_once_with('active_alerts', 'test_alert')
        alerts_service.redis_client.expire.assert_called_once_with('active_alerts', 604800)
        
        # Check stored data format
        call_args = alerts_service.redis_client.setex.call_args
        stored_key = call_args[0][0]
        stored_ttl = call_args[0][1]
        stored_data = json.loads(call_args[0][2])
        
        assert stored_key == "alert:test_alert"
        assert stored_ttl == 604800  # 7 days
        assert stored_data['type'] == 'daily_threshold'
        assert stored_data['severity'] == 'high'
        assert stored_data['service'] == 'grok'
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alerts_service):
        """Test retrieving active alerts."""
        # Mock Redis responses
        alert_ids = [b'alert1', b'alert2', b'alert3']
        alerts_service.redis_client.lrange.return_value = alert_ids
        
        def mock_get(key):
            if key == 'alert:alert1':
                return json.dumps({
                    'id': 'alert1',
                    'type': 'daily_threshold',
                    'severity': 'high',
                    'message': 'Daily cost exceeded',
                    'timestamp': '2024-10-28T10:00:00'
                })
            elif key == 'alert:alert2':
                return json.dumps({
                    'id': 'alert2',
                    'type': 'rate_limit_hit',
                    'severity': 'critical',
                    'message': 'Rate limit hit',
                    'timestamp': '2024-10-28T11:00:00'
                })
            return None
        
        alerts_service.redis_client.get.side_effect = mock_get
        
        alerts = await alerts_service.get_active_alerts(limit=10)
        
        assert len(alerts) == 2  # Only 2 alerts had data
        
        # Should be sorted by timestamp (newest first)
        assert alerts[0]['timestamp'] == '2024-10-28T11:00:00'
        assert alerts[1]['timestamp'] == '2024-10-28T10:00:00'
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alerts_service):
        """Test alert acknowledgment."""
        # Mock existing alert
        alert_data = {
            'id': 'test_alert',
            'acknowledged': False,
            'message': 'Test alert'
        }
        
        alerts_service.redis_client.get.return_value = json.dumps(alert_data)
        
        success = await alerts_service.acknowledge_alert('test_alert')
        
        assert success is True
        
        # Verify Redis operations
        alerts_service.redis_client.get.assert_called_once_with('alert:test_alert')
        alerts_service.redis_client.setex.assert_called_once()
        
        # Check that acknowledged flag was set
        call_args = alerts_service.redis_client.setex.call_args
        updated_data = json.loads(call_args[0][2])
        assert updated_data['acknowledged'] is True
    
    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self, alerts_service):
        """Test acknowledging non-existent alert."""
        alerts_service.redis_client.get.return_value = None
        
        success = await alerts_service.acknowledge_alert('nonexistent_alert')
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_update_thresholds(self, alerts_service):
        """Test updating alert thresholds."""
        new_thresholds = {
            'daily_cost_warning': 200.0,
            'daily_cost_critical': 400.0,
            'monthly_cost_warning': 3000.0
        }
        
        alerts_service.update_thresholds(new_thresholds)
        
        assert alerts_service.thresholds['daily_cost_warning'] == 200.0
        assert alerts_service.thresholds['daily_cost_critical'] == 400.0
        assert alerts_service.thresholds['monthly_cost_warning'] == 3000.0
        # Other thresholds should remain unchanged
        assert alerts_service.thresholds['monthly_cost_critical'] == 10000.0
    
    @pytest.mark.asyncio
    async def test_upgrade_messages(self, alerts_service):
        """Test upgrade recommendation messages."""
        message = alerts_service._get_upgrade_message(APIService.ALPHA_VANTAGE)
        assert 'Alpha Vantage Premium' in message
        
        message = alerts_service._get_upgrade_message(APIService.TWITTER)
        assert 'Twitter API Basic' in message
        
        message = alerts_service._get_upgrade_message(APIService.GROK)
        assert 'optimizing prompts' in message
    
    @pytest.mark.asyncio
    async def test_error_handling(self, alerts_service):
        """Test error handling in alerts service."""
        # Mock Redis error
        alerts_service.redis_client.get.side_effect = Exception("Redis error")
        
        alerts = await alerts_service.get_active_alerts()
        
        assert alerts == []  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_alert_id_generation(self, alerts_service):
        """Test alert ID generation for uniqueness."""
        # Test daily cost alert ID
        mock_totals = {'cost_today': 600.0, 'cost_this_month': 1000.0}
        alerts = await alerts_service._check_cost_thresholds(mock_totals)
        
        daily_alert = next(a for a in alerts if a.type == AlertType.DAILY_THRESHOLD)
        
        # ID should include date for uniqueness
        today = datetime.now().strftime('%Y%m%d')
        assert today in daily_alert.id
        assert 'daily_cost_critical' in daily_alert.id
    
    @pytest.mark.asyncio
    async def test_clear_old_alerts(self, alerts_service):
        """Test clearing old alerts (placeholder test)."""
        # This is a placeholder since the actual implementation relies on Redis TTL
        await alerts_service.clear_old_alerts(7)
        
        # Should complete without error
        # In a real implementation, this would test actual cleanup logic
