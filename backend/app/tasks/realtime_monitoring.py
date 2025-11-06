"""
Real-time Monitoring Celery Tasks
Manages real-time price monitoring during market hours with automatic start/stop.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from ..core.celery_app import celery_app
from ..core.database import get_db
from ..services.realtime_price_monitor import realtime_price_monitor
from ..services.sentiment_monitor import sentiment_monitor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def start_realtime_monitoring(self):
    """
    Start real-time price monitoring during market hours.
    This task runs every 15 minutes to ensure monitoring is active during market hours.
    """
    try:
        logger.info("🚀 Checking if real-time monitoring should be active")
        
        # Check if it's market hours
        if not realtime_price_monitor.is_market_hours():
            logger.info("Outside market hours, monitoring not needed")
            return {
                "status": "skipped",
                "reason": "outside_market_hours",
                "timestamp": datetime.now().isoformat()
            }
        
        # Start monitoring if not already running
        db = next(get_db())
        try:
            result = asyncio.run(realtime_price_monitor.start_monitoring(db))
            
            logger.info(f"Real-time monitoring status: {result}")
            
            return {
                "status": "success",
                "monitoring_result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"💥 Failed to start real-time monitoring: {e}")
        raise self.retry(countdown=300, exc=e)  # Retry in 5 minutes


@celery_app.task(bind=True)
def stop_realtime_monitoring(self):
    """
    Stop real-time price monitoring after market hours.
    This task runs every hour to clean up monitoring when markets are closed.
    """
    try:
        logger.info("🛑 Checking if real-time monitoring should be stopped")
        
        # Check if it's outside market hours
        if realtime_price_monitor.is_market_hours():
            logger.info("Still in market hours, keeping monitoring active")
            return {
                "status": "skipped",
                "reason": "still_market_hours",
                "timestamp": datetime.now().isoformat()
            }
        
        # Stop monitoring
        result = asyncio.run(realtime_price_monitor.stop_monitoring())
        
        logger.info(f"Real-time monitoring stopped: {result}")
        
        return {
            "status": "success",
            "stop_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"💥 Failed to stop real-time monitoring: {e}")
        raise self.retry(countdown=1800, exc=e)  # Retry in 30 minutes


@celery_app.task(bind=True)
def monitor_price_alerts(self):
    """
    Monitor for price alerts and target hits.
    This task runs every 2 minutes during market hours for quick alert detection.
    """
    try:
        # Only run during market hours
        if not realtime_price_monitor.is_market_hours():
            return {
                "status": "skipped",
                "reason": "outside_market_hours",
                "timestamp": datetime.now().isoformat()
            }
        
        logger.info("🔍 Running price alert monitoring")
        
        db = next(get_db())
        try:
            # Get symbols to monitor
            symbols = asyncio.run(realtime_price_monitor._get_symbols_to_monitor(db))
            
            if not symbols:
                return {
                    "status": "no_symbols",
                    "message": "No symbols to monitor",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Monitor all symbols for alerts
            results = asyncio.run(realtime_price_monitor._monitor_all_symbols(db))
            
            if results["alerts_triggered"] > 0:
                logger.info(f"🚨 Price alert monitoring complete: {results}")
            
            return {
                "status": "success",
                "symbols_count": len(symbols),
                "monitoring_results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"💥 Price alert monitoring failed: {e}")
        raise self.retry(countdown=120, exc=e)  # Retry in 2 minutes


@celery_app.task(bind=True)
def update_realtime_prices(self):
    """
    Update prices for all monitored symbols.
    This task runs every 1 minute during market hours for frequent price updates.
    """
    try:
        # Only run during market hours
        if not realtime_price_monitor.is_market_hours():
            return {
                "status": "skipped",
                "reason": "outside_market_hours",
                "timestamp": datetime.now().isoformat()
            }
        
        db = next(get_db())
        try:
            # Get symbols to monitor
            symbols = asyncio.run(realtime_price_monitor._get_symbols_to_monitor(db))
            
            if not symbols:
                return {
                    "status": "no_symbols",
                    "symbols_count": 0,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update prices for all symbols
            update_results = {
                "symbols_updated": 0,
                "websocket_updates": 0,
                "errors": 0
            }
            
            # Process symbols in smaller batches for frequent updates
            batch_size = 5
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                # Process batch
                for symbol in batch:
                    try:
                        result = asyncio.run(realtime_price_monitor._monitor_symbol(db, symbol))
                        if result.get("price_updated"):
                            update_results["symbols_updated"] += 1
                        if result.get("websocket_sent"):
                            update_results["websocket_updates"] += 1
                    except Exception as e:
                        update_results["errors"] += 1
                        logger.error(f"Error updating {symbol}: {e}")
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            return {
                "status": "success",
                "symbols_count": len(symbols),
                "update_results": update_results,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"💥 Real-time price update failed: {e}")
        raise self.retry(countdown=60, exc=e)  # Retry in 1 minute


@celery_app.task(bind=True)
def cleanup_monitoring_cache(self):
    """
    Clean up old monitoring cache data.
    This task runs once daily to prevent cache bloat.
    """
    try:
        logger.info("🧹 Cleaning up monitoring cache")
        
        # This would clean up old cached price data, WebSocket connections, etc.
        # Implementation depends on your Redis cache structure
        
        cleanup_results = {
            "cache_keys_cleaned": 0,
            "old_connections_closed": 0
        }
        
        # TODO: Implement cache cleanup logic
        # - Remove old pick_price:* keys
        # - Clean up old WebSocket connection data
        # - Remove expired monitoring state
        
        logger.info(f"Cache cleanup complete: {cleanup_results}")
        
        return {
            "status": "success",
            "cleanup_results": cleanup_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"💥 Cache cleanup failed: {e}")
        raise self.retry(countdown=3600, exc=e)  # Retry in 1 hour


# Manual trigger functions for testing/debugging

def trigger_start_monitoring():
    """Manually trigger real-time monitoring start."""
    return start_realtime_monitoring.delay()


def trigger_stop_monitoring():
    """Manually trigger real-time monitoring stop."""
    return stop_realtime_monitoring.delay()


def trigger_price_alerts():
    """Manually trigger price alert monitoring."""
    return monitor_price_alerts.delay()


def trigger_price_updates():
    """Manually trigger price updates."""
    return update_realtime_prices.delay()


def trigger_cache_cleanup():
    """Manually trigger cache cleanup."""
    return cleanup_monitoring_cache.delay()


@celery_app.task(bind=True)
def monitor_watchlist_sentiment(self):
    """
    Monitor sentiment for watchlist stocks and send notifications.
    Runs every 30 minutes during market hours to detect sentiment changes.
    """
    try:
        # Only run during market hours
        if not realtime_price_monitor.is_market_hours():
            return {
                "status": "skipped",
                "reason": "outside_market_hours",
                "timestamp": datetime.now().isoformat()
            }

        logger.info("🔍 Running watchlist sentiment monitoring")

        db = next(get_db())
        try:
            # Monitor sentiment for all watchlist entries
            results = asyncio.run(sentiment_monitor.monitor_watchlist_sentiment(db))

            if results["sentiment_alerts"] > 0 or results["volume_alerts"] > 0:
                logger.info(f"🚨 Sentiment monitoring complete: {results}")

            return {
                "status": "success",
                "monitoring_results": results,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"💥 Sentiment monitoring failed: {e}")
        raise self.retry(countdown=1800, exc=e)  # Retry in 30 minutes


def trigger_sentiment_monitoring():
    """Manually trigger sentiment monitoring."""
    return monitor_watchlist_sentiment.delay()
