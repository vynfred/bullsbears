"""
Performance API endpoints for BullsBears.xyz
Provides cost monitoring, usage statistics, and performance metrics
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ...services.cost_monitor import CostMonitor, APIService
from ...services.cost_alerts import CostAlertsService
from ...services.performance_logger import PerformanceLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])

@router.get("/costs")
async def get_cost_statistics() -> Dict[str, Any]:
    """
    Get comprehensive cost statistics for all API services.
    
    Returns:
        Dict containing cost statistics, usage data, and alerts
    """
    try:
        async with CostMonitor() as cost_monitor:
            stats = await cost_monitor.get_all_usage_stats()
            
            if 'error' in stats:
                raise HTTPException(status_code=500, detail=stats['error'])
            
            return {
                'status': 'success',
                'data': stats,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting cost statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usage")
async def get_usage_statistics() -> Dict[str, Any]:
    """
    Get API usage statistics with rate limit information.
    
    Returns:
        Dict containing usage statistics and rate limit status
    """
    try:
        async with CostMonitor() as cost_monitor:
            stats = await cost_monitor.get_all_usage_stats()
            
            if 'error' in stats:
                raise HTTPException(status_code=500, detail=stats['error'])
            
            # Extract usage-focused data
            usage_data = {}
            for service_name, service_data in stats['services'].items():
                usage_data[service_name] = {
                    'requests_today': service_data.get('requests_today', 0),
                    'requests_this_minute': service_data.get('requests_this_minute', 0),
                    'requests_this_month': service_data.get('requests_this_month', 0),
                    'rate_limit_hit': service_data.get('rate_limit_hit', False),
                    'upgrade_recommended': service_data.get('upgrade_recommended', False),
                    'last_request_time': service_data.get('last_request_time')
                }
            
            return {
                'status': 'success',
                'data': {
                    'services': usage_data,
                    'timestamp': stats['timestamp']
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def get_cost_trends(
    days: int = Query(7, ge=1, le=30, description="Number of days for trend analysis")
) -> Dict[str, Any]:
    """
    Get cost trends over the specified number of days.
    
    Args:
        days: Number of days to analyze (1-30)
        
    Returns:
        Dict containing daily cost trends and projections
    """
    try:
        async with CostMonitor() as cost_monitor:
            trends = await cost_monitor.get_cost_trends(days)
            
            if 'error' in trends:
                raise HTTPException(status_code=500, detail=trends['error'])
            
            return {
                'status': 'success',
                'data': trends,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting cost trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_active_alerts(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of alerts to return")
) -> Dict[str, Any]:
    """
    Get active cost and usage alerts.
    
    Args:
        limit: Maximum number of alerts to return (1-100)
        
    Returns:
        Dict containing active alerts
    """
    try:
        async with CostAlertsService() as alerts_service:
            alerts = await alerts_service.get_active_alerts(limit)
            
            return {
                'status': 'success',
                'data': {
                    'alerts': alerts,
                    'count': len(alerts)
                },
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    """
    Acknowledge an alert (mark as read).
    
    Args:
        alert_id: ID of the alert to acknowledge
        
    Returns:
        Dict containing acknowledgment status
    """
    try:
        async with CostAlertsService() as alerts_service:
            success = await alerts_service.acknowledge_alert(alert_id)
            
            if not success:
                raise HTTPException(status_code=404, detail="Alert not found")
            
            return {
                'status': 'success',
                'message': f'Alert {alert_id} acknowledged',
                'timestamp': datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations")
async def get_upgrade_recommendations() -> Dict[str, Any]:
    """
    Get API upgrade recommendations based on current usage patterns.
    
    Returns:
        Dict containing upgrade recommendations
    """
    try:
        async with CostMonitor() as cost_monitor:
            recommendations = await cost_monitor.get_upgrade_recommendations()
            
            return {
                'status': 'success',
                'data': {
                    'recommendations': recommendations,
                    'count': len(recommendations)
                },
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting upgrade recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_performance_summary() -> Dict[str, Any]:
    """
    Get comprehensive performance summary including costs, usage, and alerts.
    
    Returns:
        Dict containing complete performance overview
    """
    try:
        async with CostMonitor() as cost_monitor, CostAlertsService() as alerts_service:
            # Get cost statistics
            cost_stats = await cost_monitor.get_all_usage_stats()
            
            # Get active alerts
            alerts = await alerts_service.get_active_alerts(10)  # Top 10 alerts
            
            # Get upgrade recommendations
            recommendations = await cost_monitor.get_upgrade_recommendations()
            
            # Get cost trends (7 days)
            trends = await cost_monitor.get_cost_trends(7)
            
            return {
                'status': 'success',
                'data': {
                    'costs': cost_stats,
                    'alerts': {
                        'active': alerts,
                        'count': len(alerts)
                    },
                    'recommendations': {
                        'upgrades': recommendations,
                        'count': len(recommendations)
                    },
                    'trends': trends
                },
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def get_performance_health() -> Dict[str, Any]:
    """
    Get performance monitoring system health status.
    
    Returns:
        Dict containing system health information
    """
    try:
        health_status = {
            'cost_monitor': 'healthy',
            'alerts_service': 'healthy',
            'redis_connection': 'healthy',
            'api_services': {}
        }
        
        # Test cost monitor
        try:
            async with CostMonitor() as cost_monitor:
                await cost_monitor.get_all_usage_stats()
        except Exception as e:
            health_status['cost_monitor'] = f'unhealthy: {str(e)}'
        
        # Test alerts service
        try:
            async with CostAlertsService() as alerts_service:
                await alerts_service.get_active_alerts(1)
        except Exception as e:
            health_status['alerts_service'] = f'unhealthy: {str(e)}'
        
        # Check API service status
        for service in APIService:
            health_status['api_services'][service.value] = 'monitored'
        
        overall_health = 'healthy' if all(
            status == 'healthy' or status == 'monitored' 
            for status in [health_status['cost_monitor'], health_status['alerts_service']]
        ) else 'degraded'
        
        return {
            'status': 'success',
            'data': {
                'overall_health': overall_health,
                'components': health_status
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-daily")
async def reset_daily_counters() -> Dict[str, Any]:
    """
    Reset daily usage counters (typically called by cron job).
    
    Returns:
        Dict containing reset status
    """
    try:
        async with CostMonitor() as cost_monitor:
            await cost_monitor.reset_daily_counters()
            
            return {
                'status': 'success',
                'message': 'Daily counters reset successfully',
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error resetting daily counters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/service/{service_name}")
async def get_service_statistics(service_name: str) -> Dict[str, Any]:
    """
    Get detailed statistics for a specific API service.
    
    Args:
        service_name: Name of the API service
        
    Returns:
        Dict containing detailed service statistics
    """
    try:
        # Validate service name
        try:
            service = APIService(service_name.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid service name: {service_name}")
        
        async with CostMonitor() as cost_monitor:
            all_stats = await cost_monitor.get_all_usage_stats()
            
            if 'error' in all_stats:
                raise HTTPException(status_code=500, detail=all_stats['error'])
            
            service_data = all_stats['services'].get(service.value)
            if not service_data:
                raise HTTPException(status_code=404, detail=f"No data found for service: {service_name}")
            
            return {
                'status': 'success',
                'data': {
                    'service': service.value,
                    'statistics': service_data,
                    'limits': cost_monitor.api_limits[service].__dict__
                },
                'timestamp': datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service statistics for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
