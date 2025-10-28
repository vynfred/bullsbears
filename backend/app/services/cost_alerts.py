"""
Cost Alerts Service for BullsBears.xyz
Handles cost threshold monitoring, alert generation, and notification management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..core.redis_client import get_redis_client
from .cost_monitor import CostMonitor, APIService

logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types of cost alerts."""
    DAILY_THRESHOLD = "daily_threshold"
    MONTHLY_THRESHOLD = "monthly_threshold"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    RATE_LIMIT_HIT = "rate_limit_hit"
    UPGRADE_RECOMMENDED = "upgrade_recommended"

class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Alert:
    """Alert data structure."""
    id: str
    type: AlertType
    severity: AlertSeverity
    service: Optional[APIService] = None
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: datetime = None
    acknowledged: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}

class CostAlertsService:
    """
    Service for managing cost alerts and notifications.
    Integrates with CostMonitor to provide comprehensive alert management.
    """
    
    def __init__(self):
        self.redis_client = None
        self.cost_monitor = None
        
        # Default alert thresholds (can be configured)
        self.thresholds = {
            'daily_cost_warning': 300.0,    # $3/day warning
            'daily_cost_critical': 500.0,   # $5/day critical
            'monthly_cost_warning': 5000.0, # $50/month warning
            'monthly_cost_critical': 10000.0, # $100/month critical
            'rate_limit_warning': 80.0,     # 80% utilization warning
            'rate_limit_critical': 95.0     # 95% utilization critical
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.redis_client = await get_redis_client()
        self.cost_monitor = CostMonitor()
        await self.cost_monitor.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.cost_monitor:
            await self.cost_monitor.__aexit__(exc_type, exc_val, exc_tb)
        if self.redis_client:
            await self.redis_client.close()
    
    async def check_all_alerts(self) -> List[Alert]:
        """Check all alert conditions and generate alerts as needed."""
        alerts = []
        
        try:
            # Get current usage statistics
            usage_stats = await self.cost_monitor.get_all_usage_stats()
            
            if 'error' in usage_stats:
                return alerts
            
            # Check cost thresholds
            cost_alerts = await self._check_cost_thresholds(usage_stats['totals'])
            alerts.extend(cost_alerts)
            
            # Check rate limit alerts for each service
            for service_name, service_data in usage_stats['services'].items():
                service = APIService(service_name)
                rate_limit_alerts = await self._check_rate_limit_alerts(service, service_data)
                alerts.extend(rate_limit_alerts)
            
            # Store new alerts
            for alert in alerts:
                await self._store_alert(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    async def _check_cost_thresholds(self, totals: Dict[str, Any]) -> List[Alert]:
        """Check if cost thresholds have been exceeded."""
        alerts = []
        
        daily_cost = totals.get('cost_today', 0.0)
        monthly_cost = totals.get('cost_this_month', 0.0)
        
        # Daily cost alerts
        if daily_cost >= self.thresholds['daily_cost_critical']:
            alerts.append(Alert(
                id=f"daily_cost_critical_{datetime.now().strftime('%Y%m%d')}",
                type=AlertType.DAILY_THRESHOLD,
                severity=AlertSeverity.CRITICAL,
                message=f"Daily cost threshold exceeded: ${daily_cost/100:.2f}",
                details={
                    'current_cost': daily_cost,
                    'threshold': self.thresholds['daily_cost_critical'],
                    'cost_usd': daily_cost / 100
                }
            ))
        elif daily_cost >= self.thresholds['daily_cost_warning']:
            alerts.append(Alert(
                id=f"daily_cost_warning_{datetime.now().strftime('%Y%m%d')}",
                type=AlertType.DAILY_THRESHOLD,
                severity=AlertSeverity.MEDIUM,
                message=f"Daily cost warning: ${daily_cost/100:.2f}",
                details={
                    'current_cost': daily_cost,
                    'threshold': self.thresholds['daily_cost_warning'],
                    'cost_usd': daily_cost / 100
                }
            ))
        
        # Monthly cost alerts
        if monthly_cost >= self.thresholds['monthly_cost_critical']:
            alerts.append(Alert(
                id=f"monthly_cost_critical_{datetime.now().strftime('%Y%m')}",
                type=AlertType.MONTHLY_THRESHOLD,
                severity=AlertSeverity.CRITICAL,
                message=f"Monthly cost threshold exceeded: ${monthly_cost/100:.2f}",
                details={
                    'current_cost': monthly_cost,
                    'threshold': self.thresholds['monthly_cost_critical'],
                    'cost_usd': monthly_cost / 100
                }
            ))
        elif monthly_cost >= self.thresholds['monthly_cost_warning']:
            alerts.append(Alert(
                id=f"monthly_cost_warning_{datetime.now().strftime('%Y%m')}",
                type=AlertType.MONTHLY_THRESHOLD,
                severity=AlertSeverity.MEDIUM,
                message=f"Monthly cost warning: ${monthly_cost/100:.2f}",
                details={
                    'current_cost': monthly_cost,
                    'threshold': self.thresholds['monthly_cost_warning'],
                    'cost_usd': monthly_cost / 100
                }
            ))
        
        return alerts
    
    async def _check_rate_limit_alerts(self, service: APIService, service_data: Dict[str, Any]) -> List[Alert]:
        """Check rate limit alerts for a specific service."""
        alerts = []
        
        if service_data.get('rate_limit_hit'):
            alerts.append(Alert(
                id=f"rate_limit_hit_{service.value}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                type=AlertType.RATE_LIMIT_HIT,
                severity=AlertSeverity.CRITICAL,
                service=service,
                message=f"Rate limit hit for {service.value}",
                details={
                    'service': service.value,
                    'requests_today': service_data.get('requests_today', 0),
                    'requests_this_minute': service_data.get('requests_this_minute', 0)
                }
            ))
        elif service_data.get('upgrade_recommended'):
            alerts.append(Alert(
                id=f"upgrade_recommended_{service.value}_{datetime.now().strftime('%Y%m%d')}",
                type=AlertType.UPGRADE_RECOMMENDED,
                severity=AlertSeverity.MEDIUM,
                service=service,
                message=f"Upgrade recommended for {service.value}",
                details={
                    'service': service.value,
                    'utilization_percent': service_data.get('utilization_percent', 0),
                    'upgrade_message': self._get_upgrade_message(service)
                }
            ))
        
        return alerts
    
    def _get_upgrade_message(self, service: APIService) -> str:
        """Get upgrade recommendation message for a specific service."""
        messages = {
            APIService.ALPHA_VANTAGE: "Consider upgrading to Alpha Vantage Premium for higher rate limits",
            APIService.NEWSAPI: "Consider upgrading to NewsAPI Commercial plan for higher limits",
            APIService.TWITTER: "Consider upgrading to Twitter API Basic or Enterprise",
            APIService.FMP: "Consider upgrading FMP subscription for higher rate limits",
            APIService.REDDIT: "Consider implementing OAuth for higher rate limits",
            APIService.GROK: "Consider optimizing prompts to reduce token usage",
            APIService.DEEPSEEK: "Consider optimizing prompts to reduce token usage"
        }
        return messages.get(service, f"Consider upgrading {service.value} API subscription")
    
    async def _store_alert(self, alert: Alert):
        """Store alert in Redis for dashboard display."""
        try:
            if not self.redis_client:
                return
            
            alert_key = f"alert:{alert.id}"
            alert_data = asdict(alert)
            
            # Convert enum values to strings for JSON serialization
            alert_data['type'] = alert.type.value
            alert_data['severity'] = alert.severity.value
            if alert.service:
                alert_data['service'] = alert.service.value
            alert_data['timestamp'] = alert.timestamp.isoformat()
            
            # Store alert with 7-day TTL
            await self.redis_client.setex(
                alert_key,
                604800,  # 7 days
                json.dumps(alert_data, default=str)
            )
            
            # Add to alerts list for dashboard
            await self.redis_client.lpush('active_alerts', alert.id)
            await self.redis_client.expire('active_alerts', 604800)  # 7 days TTL
            
        except Exception as e:
            logger.error(f"Error storing alert {alert.id}: {e}")
    
    async def get_active_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get active alerts for dashboard display."""
        try:
            if not self.redis_client:
                return []
            
            # Get alert IDs from the list
            alert_ids = await self.redis_client.lrange('active_alerts', 0, limit - 1)
            
            alerts = []
            for alert_id in alert_ids:
                alert_key = f"alert:{alert_id.decode() if isinstance(alert_id, bytes) else alert_id}"
                alert_data = await self.redis_client.get(alert_key)
                
                if alert_data:
                    alert_dict = json.loads(alert_data)
                    alerts.append(alert_dict)
            
            # Sort by timestamp (newest first)
            alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert (mark as read)."""
        try:
            if not self.redis_client:
                return False
            
            alert_key = f"alert:{alert_id}"
            alert_data = await self.redis_client.get(alert_key)
            
            if alert_data:
                alert_dict = json.loads(alert_data)
                alert_dict['acknowledged'] = True
                
                await self.redis_client.setex(
                    alert_key,
                    604800,  # 7 days
                    json.dumps(alert_dict, default=str)
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    async def clear_old_alerts(self, days: int = 7):
        """Clear alerts older than specified days."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # This would be implemented with a more sophisticated cleanup
            # For now, Redis TTL handles automatic cleanup
            logger.info(f"Alert cleanup completed for alerts older than {days} days")
            
        except Exception as e:
            logger.error(f"Error clearing old alerts: {e}")
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.thresholds.update(new_thresholds)
        logger.info(f"Alert thresholds updated: {new_thresholds}")
