"""
Cost Monitor Service for BullsBears.xyz API Usage Tracking
Comprehensive real-time API usage tracking and cost estimation across all services
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..core.redis_client import get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)

class APIService(Enum):
    """Enumeration of all tracked API services."""
    GROK = "grok"
    DEEPSEEK = "deepseek"
    ALPHA_VANTAGE = "alpha_vantage"
    NEWSAPI = "newsapi"
    REDDIT = "reddit"
    TWITTER = "twitter"
    FMP = "fmp"
    FINNHUB = "finnhub"
    POLYGON = "polygon"

@dataclass
class APILimits:
    """Rate limits and cost information for each API service."""
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    requests_per_month: Optional[int] = None
    cost_per_request: float = 0.0  # in cents
    cost_per_token: Optional[float] = None  # for AI services
    burst_limit: Optional[int] = None
    burst_window: int = 60  # seconds

@dataclass
class APIUsage:
    """Current usage statistics for an API service."""
    service: APIService
    requests_today: int = 0
    requests_this_minute: int = 0
    requests_this_month: int = 0
    tokens_used: int = 0
    cost_today: float = 0.0  # in cents
    cost_this_month: float = 0.0  # in cents
    last_request_time: Optional[datetime] = None
    rate_limit_hit: bool = False
    upgrade_recommended: bool = False

@dataclass
class CostAlert:
    """Cost alert configuration and status."""
    threshold_daily: float = 500.0  # cents ($5/day default)
    threshold_monthly: float = 10000.0  # cents ($100/month default)
    alert_triggered: bool = False
    last_alert_time: Optional[datetime] = None

class CostMonitor:
    """
    Comprehensive API usage tracking and cost monitoring service.
    Tracks all API services with real-time rate limit monitoring and cost estimation.
    """
    
    def __init__(self):
        self.redis_client = None
        self.api_limits = self._initialize_api_limits()
        self.usage_cache = {}
        self.cost_alert = CostAlert()
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.redis_client = await get_redis_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _initialize_api_limits(self) -> Dict[APIService, APILimits]:
        """Initialize API limits and cost information for all services."""
        return {
            APIService.GROK: APILimits(
                cost_per_token=0.0002,  # 2¢ per analysis estimate
                cost_per_request=2.0    # 2¢ per analysis
            ),
            APIService.DEEPSEEK: APILimits(
                cost_per_token=0.0001,  # 1¢ per analysis estimate
                cost_per_request=1.0    # 1¢ per analysis
            ),
            APIService.ALPHA_VANTAGE: APILimits(
                requests_per_minute=5,
                requests_per_day=25,
                cost_per_request=0.0    # Free tier
            ),
            APIService.NEWSAPI: APILimits(
                requests_per_day=1000,
                burst_limit=100,
                burst_window=86400,     # 24 hours
                cost_per_request=0.0    # Free tier
            ),
            APIService.REDDIT: APILimits(
                requests_per_minute=60,  # Unauthenticated
                cost_per_request=0.0     # Free
            ),
            APIService.TWITTER: APILimits(
                requests_per_minute=60,  # 900 per 15 minutes = ~60/min
                requests_per_month=500000,  # 500k posts/month read
                cost_per_request=0.0     # Free tier
            ),
            APIService.FMP: APILimits(
                requests_per_minute=300,  # Premium tier estimate
                cost_per_request=0.01     # Estimate
            ),
            APIService.FINNHUB: APILimits(
                requests_per_minute=60,
                cost_per_request=0.0      # Free tier
            ),
            APIService.POLYGON: APILimits(
                requests_per_minute=5,    # Free tier
                cost_per_request=0.0
            )
        }
    
    async def track_api_call(
        self, 
        service: APIService, 
        tokens_used: int = 0,
        request_cost: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Track an API call and update usage statistics.
        
        Args:
            service: The API service being called
            tokens_used: Number of tokens used (for AI services)
            request_cost: Actual cost if known, otherwise estimated
            
        Returns:
            Dict with usage statistics and rate limit status
        """
        try:
            current_time = datetime.now()
            usage_key = f"api_usage:{service.value}"
            
            # Get current usage from Redis
            usage_data = await self._get_usage_from_redis(usage_key)
            if not usage_data:
                usage_data = APIUsage(service=service)
            
            # Update usage statistics
            usage_data.requests_today += 1
            usage_data.requests_this_minute += 1
            usage_data.requests_this_month += 1
            usage_data.tokens_used += tokens_used
            usage_data.last_request_time = current_time
            
            # Calculate cost
            limits = self.api_limits[service]
            if request_cost is not None:
                cost = request_cost
            elif tokens_used > 0 and limits.cost_per_token:
                cost = tokens_used * limits.cost_per_token * 100  # Convert to cents
            else:
                cost = limits.cost_per_request
            
            usage_data.cost_today += cost
            usage_data.cost_this_month += cost
            
            # Check rate limits
            rate_limit_status = await self._check_rate_limits(service, usage_data)
            usage_data.rate_limit_hit = rate_limit_status['limit_hit']
            usage_data.upgrade_recommended = rate_limit_status['upgrade_recommended']
            
            # Store updated usage in Redis
            await self._store_usage_in_redis(usage_key, usage_data)
            
            # Check cost alerts
            await self._check_cost_alerts(usage_data.cost_today, usage_data.cost_this_month)
            
            return {
                'service': service.value,
                'usage': asdict(usage_data),
                'rate_limit_status': rate_limit_status,
                'cost_today': usage_data.cost_today,
                'cost_this_month': usage_data.cost_this_month
            }
            
        except Exception as e:
            logger.error(f"Error tracking API call for {service.value}: {e}")
            return {'error': str(e)}
    
    async def _get_usage_from_redis(self, usage_key: str) -> Optional[APIUsage]:
        """Retrieve usage data from Redis."""
        try:
            if not self.redis_client:
                return None
                
            data = await self.redis_client.get(usage_key)
            if data:
                usage_dict = json.loads(data)
                # Convert string back to enum
                usage_dict['service'] = APIService(usage_dict['service'])
                # Convert datetime strings back to datetime objects
                if usage_dict.get('last_request_time'):
                    usage_dict['last_request_time'] = datetime.fromisoformat(
                        usage_dict['last_request_time']
                    )
                return APIUsage(**usage_dict)
            return None
        except Exception as e:
            logger.error(f"Error retrieving usage from Redis: {e}")
            return None
    
    async def _store_usage_in_redis(self, usage_key: str, usage_data: APIUsage):
        """Store usage data in Redis with appropriate TTL."""
        try:
            if not self.redis_client:
                return
                
            # Convert to dict for JSON serialization
            usage_dict = asdict(usage_data)
            usage_dict['service'] = usage_data.service.value
            if usage_data.last_request_time:
                usage_dict['last_request_time'] = usage_data.last_request_time.isoformat()
            
            # Store with 24-hour TTL
            await self.redis_client.setex(
                usage_key, 
                86400,  # 24 hours
                json.dumps(usage_dict, default=str)
            )
        except Exception as e:
            logger.error(f"Error storing usage in Redis: {e}")
    
    async def _check_rate_limits(
        self, 
        service: APIService, 
        usage_data: APIUsage
    ) -> Dict[str, Any]:
        """Check if rate limits are being approached or exceeded."""
        limits = self.api_limits[service]
        status = {
            'limit_hit': False,
            'upgrade_recommended': False,
            'utilization_percent': 0.0,
            'time_until_reset': 0
        }
        
        # Check daily limits
        if limits.requests_per_day:
            daily_utilization = (usage_data.requests_today / limits.requests_per_day) * 100
            status['utilization_percent'] = max(status['utilization_percent'], daily_utilization)
            
            if usage_data.requests_today >= limits.requests_per_day:
                status['limit_hit'] = True
            elif daily_utilization > 80:
                status['upgrade_recommended'] = True
        
        # Check minute limits
        if limits.requests_per_minute:
            minute_utilization = (usage_data.requests_this_minute / limits.requests_per_minute) * 100
            status['utilization_percent'] = max(status['utilization_percent'], minute_utilization)
            
            if usage_data.requests_this_minute >= limits.requests_per_minute:
                status['limit_hit'] = True
            elif minute_utilization > 80:
                status['upgrade_recommended'] = True
        
        return status
    
    async def _check_cost_alerts(self, cost_today: float, cost_this_month: float):
        """Check if cost thresholds have been exceeded."""
        alert_triggered = False
        
        if cost_today > self.cost_alert.threshold_daily:
            alert_triggered = True
            logger.warning(f"Daily cost threshold exceeded: ${cost_today/100:.2f}")
        
        if cost_this_month > self.cost_alert.threshold_monthly:
            alert_triggered = True
            logger.warning(f"Monthly cost threshold exceeded: ${cost_this_month/100:.2f}")
        
        if alert_triggered and not self.cost_alert.alert_triggered:
            self.cost_alert.alert_triggered = True
            self.cost_alert.last_alert_time = datetime.now()
            await self._send_cost_alert(cost_today, cost_this_month)
    
    async def _send_cost_alert(self, cost_today: float, cost_this_month: float):
        """Send cost alert (dashboard notification for now)."""
        alert_data = {
            'type': 'cost_alert',
            'cost_today': cost_today,
            'cost_this_month': cost_this_month,
            'threshold_daily': self.cost_alert.threshold_daily,
            'threshold_monthly': self.cost_alert.threshold_monthly,
            'timestamp': datetime.now().isoformat()
        }

        try:
            if self.redis_client:
                await self.redis_client.lpush('cost_alerts', json.dumps(alert_data))
                await self.redis_client.expire('cost_alerts', 86400)  # 24 hour TTL
        except Exception as e:
            logger.error(f"Error sending cost alert: {e}")

    async def _get_usage_from_redis(self, usage_key: str) -> Optional[APIUsage]:
        """Retrieve usage data from Redis."""
        try:
            if not self.redis_client:
                return None

            data = await self.redis_client.get(usage_key)
            if data:
                usage_dict = json.loads(data)
                # Convert string back to enum
                usage_dict['service'] = APIService(usage_dict['service'])
                # Convert datetime strings back to datetime objects
                if usage_dict.get('last_request_time'):
                    usage_dict['last_request_time'] = datetime.fromisoformat(
                        usage_dict['last_request_time']
                    )
                return APIUsage(**usage_dict)
            return None
        except Exception as e:
            logger.error(f"Error retrieving usage from Redis: {e}")
            return None

    async def _store_usage_in_redis(self, usage_key: str, usage_data: APIUsage):
        """Store usage data in Redis with appropriate TTL."""
        try:
            if not self.redis_client:
                return

            # Convert to dict for JSON serialization
            usage_dict = asdict(usage_data)
            usage_dict['service'] = usage_data.service.value
            if usage_data.last_request_time:
                usage_dict['last_request_time'] = usage_data.last_request_time.isoformat()

            # Store with 24-hour TTL
            await self.redis_client.setex(
                usage_key,
                86400,  # 24 hours
                json.dumps(usage_dict, default=str)
            )
        except Exception as e:
            logger.error(f"Error storing usage in Redis: {e}")

    async def _check_rate_limits(
        self,
        service: APIService,
        usage_data: APIUsage
    ) -> Dict[str, Any]:
        """Check if rate limits are being approached or exceeded."""
        limits = self.api_limits[service]
        status = {
            'limit_hit': False,
            'upgrade_recommended': False,
            'utilization_percent': 0.0,
            'time_until_reset': 0
        }

        # Check daily limits
        if limits.requests_per_day:
            daily_utilization = (usage_data.requests_today / limits.requests_per_day) * 100
            status['utilization_percent'] = max(status['utilization_percent'], daily_utilization)

            if usage_data.requests_today >= limits.requests_per_day:
                status['limit_hit'] = True
            elif daily_utilization > 80:
                status['upgrade_recommended'] = True

        # Check minute limits
        if limits.requests_per_minute:
            minute_utilization = (usage_data.requests_this_minute / limits.requests_per_minute) * 100
            status['utilization_percent'] = max(status['utilization_percent'], minute_utilization)

            if usage_data.requests_this_minute >= limits.requests_per_minute:
                status['limit_hit'] = True
            elif minute_utilization > 80:
                status['upgrade_recommended'] = True

        return status

    async def _check_cost_alerts(self, cost_today: float, cost_this_month: float):
        """Check if cost thresholds have been exceeded."""
        alert_triggered = False

        if cost_today > self.cost_alert.threshold_daily:
            alert_triggered = True
            logger.warning(f"Daily cost threshold exceeded: ${cost_today/100:.2f}")

        if cost_this_month > self.cost_alert.threshold_monthly:
            alert_triggered = True
            logger.warning(f"Monthly cost threshold exceeded: ${cost_this_month/100:.2f}")

        if alert_triggered and not self.cost_alert.alert_triggered:
            self.cost_alert.alert_triggered = True
            self.cost_alert.last_alert_time = datetime.now()
            await self._send_cost_alert(cost_today, cost_this_month)

    async def get_all_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics for all API services."""
        try:
            all_stats = {}
            total_cost_today = 0.0
            total_cost_month = 0.0

            for service in APIService:
                usage_key = f"api_usage:{service.value}"
                usage_data = await self._get_usage_from_redis(usage_key)

                if usage_data:
                    all_stats[service.value] = asdict(usage_data)
                    total_cost_today += usage_data.cost_today
                    total_cost_month += usage_data.cost_this_month
                else:
                    all_stats[service.value] = asdict(APIUsage(service=service))

            return {
                'services': all_stats,
                'totals': {
                    'cost_today': total_cost_today,
                    'cost_this_month': total_cost_month,
                    'cost_today_usd': total_cost_today / 100,
                    'cost_this_month_usd': total_cost_month / 100
                },
                'alerts': asdict(self.cost_alert),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {'error': str(e)}

    async def get_cost_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get cost trends over the specified number of days."""
        try:
            trends = {}
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                date_key = date.strftime('%Y-%m-%d')
                daily_cost = await self._get_daily_cost(date_key)
                trends[date_key] = daily_cost

            return {
                'daily_trends': trends,
                'average_daily_cost': sum(trends.values()) / len(trends) if trends else 0,
                'projected_monthly_cost': (sum(trends.values()) / len(trends)) * 30 if trends else 0
            }

        except Exception as e:
            logger.error(f"Error getting cost trends: {e}")
            return {'error': str(e)}

    async def _get_daily_cost(self, date_key: str) -> float:
        """Get total cost for a specific date."""
        try:
            if not self.redis_client:
                return 0.0

            cost_key = f"daily_cost:{date_key}"
            cost_data = await self.redis_client.get(cost_key)
            return float(cost_data) if cost_data else 0.0

        except Exception as e:
            logger.error(f"Error getting daily cost for {date_key}: {e}")
            return 0.0

    async def reset_daily_counters(self):
        """Reset daily counters (called by cron job)."""
        try:
            for service in APIService:
                usage_key = f"api_usage:{service.value}"
                usage_data = await self._get_usage_from_redis(usage_key)

                if usage_data:
                    # Store daily cost for historical tracking
                    date_key = datetime.now().strftime('%Y-%m-%d')
                    cost_key = f"daily_cost:{date_key}"
                    await self.redis_client.setex(cost_key, 86400 * 30, str(usage_data.cost_today))  # 30 days TTL

                    # Reset daily counters
                    usage_data.requests_today = 0
                    usage_data.cost_today = 0.0
                    usage_data.requests_this_minute = 0

                    await self._store_usage_in_redis(usage_key, usage_data)

            # Reset cost alert
            self.cost_alert.alert_triggered = False

        except Exception as e:
            logger.error(f"Error resetting daily counters: {e}")

    async def get_upgrade_recommendations(self) -> List[Dict[str, Any]]:
        """Get upgrade recommendations for APIs approaching limits."""
        recommendations = []

        try:
            for service in APIService:
                usage_key = f"api_usage:{service.value}"
                usage_data = await self._get_usage_from_redis(usage_key)

                if usage_data and usage_data.upgrade_recommended:
                    limits = self.api_limits[service]

                    recommendation = {
                        'service': service.value,
                        'current_usage': {
                            'requests_today': usage_data.requests_today,
                            'requests_this_minute': usage_data.requests_this_minute
                        },
                        'limits': {
                            'requests_per_day': limits.requests_per_day,
                            'requests_per_minute': limits.requests_per_minute
                        },
                        'recommendation': self._get_upgrade_message(service),
                        'priority': 'HIGH' if usage_data.rate_limit_hit else 'MEDIUM'
                    }
                    recommendations.append(recommendation)

            return recommendations

        except Exception as e:
            logger.error(f"Error getting upgrade recommendations: {e}")
            return []

    def _get_upgrade_message(self, service: APIService) -> str:
        """Get upgrade recommendation message for a specific service."""
        messages = {
            APIService.ALPHA_VANTAGE: "Consider upgrading to Alpha Vantage Premium for higher rate limits and real-time data",
            APIService.NEWSAPI: "Consider upgrading to NewsAPI Commercial plan ($449+/mo) for higher limits",
            APIService.TWITTER: "Consider upgrading to Twitter API Basic ($100/mo) or Enterprise for higher limits",
            APIService.FMP: "Consider upgrading FMP subscription for higher rate limits",
            APIService.REDDIT: "Consider implementing OAuth for Reddit API to get 600 requests/10min",
            APIService.GROK: "Monitor Grok API usage - consider optimizing prompts to reduce token usage",
            APIService.DEEPSEEK: "Monitor DeepSeek API usage - consider optimizing prompts to reduce token usage"
        }
        return messages.get(service, f"Consider upgrading {service.value} API subscription")
