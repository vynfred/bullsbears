"""
Celery tasks for watchlist notification checking.
Runs automated checks for target hits, stop losses, and performance milestones.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from celery import Celery

from ..core.database import get_db
from ..services.watchlist_notifications import WatchlistNotificationService, WatchlistNotification
from ..models.watchlist import WatchlistEntry

logger = logging.getLogger(__name__)

# Initialize Celery app (this would be configured in main celery config)
celery_app = Celery('bullsbears')


@celery_app.task(name="check_watchlist_notifications")
def check_watchlist_notifications() -> Dict[str, Any]:
    """
    Celery task to check all watchlist entries for notification conditions.
    Runs every 15 minutes during market hours.
    """
    logger.info("Starting watchlist notification check")
    
    db = next(get_db())
    try:
        notification_service = WatchlistNotificationService()
        
        # Check all watchlist alerts
        notifications = notification_service.check_all_watchlist_alerts(db)
        
        # Process notifications (send to frontend, store in DB, etc.)
        processed_notifications = []
        for notification in notifications:
            processed = process_notification(notification)
            if processed:
                processed_notifications.append(processed)
        
        result = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "notifications_found": len(notifications),
            "notifications_processed": len(processed_notifications),
            "notifications": [
                {
                    "symbol": n.symbol,
                    "type": n.notification_type.value,
                    "severity": n.severity.value,
                    "title": n.title,
                    "gain_percent": n.gain_percent
                }
                for n in notifications
            ]
        }
        
        logger.info(f"Notification check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in notification check task: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "notifications_found": 0,
            "notifications_processed": 0
        }
    finally:
        db.close()


@celery_app.task(name="generate_daily_summary")
def generate_daily_summary() -> Dict[str, Any]:
    """
    Celery task to generate daily watchlist performance summary.
    Runs once per day at market close.
    """
    logger.info("Generating daily watchlist summary")
    
    db = next(get_db())
    try:
        notification_service = WatchlistNotificationService()
        
        # Generate daily summary
        summary = notification_service.generate_daily_summary(db)
        
        if summary:
            # Process the summary notification
            processed = process_notification(summary)
            
            result = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "summary_generated": True,
                "summary": {
                    "title": summary.title,
                    "message": summary.message,
                    "gain_percent": summary.gain_percent,
                    "gain_dollars": summary.gain_dollars,
                    "metadata": summary.metadata
                }
            }
        else:
            result = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "summary_generated": False,
                "message": "No active watchlist entries"
            }
        
        logger.info(f"Daily summary completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in daily summary task: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "summary_generated": False
        }
    finally:
        db.close()


@celery_app.task(name="check_market_hours_notifications")
def check_market_hours_notifications() -> Dict[str, Any]:
    """
    Celery task to check notifications only during market hours.
    Runs every 5 minutes during market hours (9:30 AM - 4:00 PM ET, Mon-Fri).
    """
    # Check if it's market hours
    now = datetime.utcnow()
    # Convert to ET (approximate, doesn't handle DST perfectly)
    et_hour = (now.hour - 5) % 24
    is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
    is_market_hours = is_weekday and 9 <= et_hour <= 16
    
    if not is_market_hours:
        return {
            "status": "skipped",
            "timestamp": datetime.now().isoformat(),
            "reason": "outside_market_hours",
            "current_et_hour": et_hour,
            "is_weekday": is_weekday
        }
    
    # Run the regular notification check
    return check_watchlist_notifications()


def process_notification(notification: WatchlistNotification) -> Dict[str, Any]:
    """
    Process a notification by sending it to appropriate channels.
    This could include WebSocket, push notifications, email, etc.
    """
    try:
        # Log the notification
        logger.info(f"Processing notification: {notification.title} - {notification.message}")
        
        # Here you would implement actual notification delivery:
        # - WebSocket broadcast to frontend
        # - Push notification to mobile app
        # - Email notification
        # - Store in notifications table
        
        # For now, just return the processed notification data
        return {
            "id": notification.id,
            "symbol": notification.symbol,
            "type": notification.notification_type.value,
            "severity": notification.severity.value,
            "title": notification.title,
            "message": notification.message,
            "processed_at": datetime.now().isoformat(),
            "delivery_channels": ["log"]  # Would include actual channels
        }
        
    except Exception as e:
        logger.error(f"Error processing notification {notification.id}: {e}")
        return None


@celery_app.task(name="cleanup_old_notifications")
def cleanup_old_notifications(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Celery task to clean up old notifications.
    Runs daily to remove notifications older than specified days.
    """
    logger.info(f"Cleaning up notifications older than {days_to_keep} days")
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # This would delete old notifications from the database
        # For now, just log the cleanup operation
        
        result = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "cutoff_date": cutoff_date.isoformat(),
            "days_to_keep": days_to_keep,
            "notifications_deleted": 0  # Would be actual count
        }
        
        logger.info(f"Notification cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in notification cleanup task: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "notifications_deleted": 0
        }


# Task scheduling configuration (would be in celery beat schedule)
NOTIFICATION_SCHEDULE = {
    'check-watchlist-notifications': {
        'task': 'check_watchlist_notifications',
        'schedule': 900.0,  # Every 15 minutes
    },
    'check-market-hours-notifications': {
        'task': 'check_market_hours_notifications',
        'schedule': 300.0,  # Every 5 minutes
    },
    'generate-daily-summary': {
        'task': 'generate_daily_summary',
        'schedule': {
            'hour': 21,  # 9 PM UTC (4 PM ET)
            'minute': 0,
        },
    },
    'cleanup-old-notifications': {
        'task': 'cleanup_old_notifications',
        'schedule': {
            'hour': 2,  # 2 AM UTC
            'minute': 0,
        },
    },
}


if __name__ == "__main__":
    # For testing purposes
    print("Testing notification checker...")
    result = check_watchlist_notifications()
    print(f"Result: {result}")
