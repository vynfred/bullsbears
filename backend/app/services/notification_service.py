"""
Notification Service for Watchlist Monitoring Alerts.

Handles WebSocket push notifications and in-app banners for monitoring events.
Integrates with Redis for real-time messaging and PWA push notifications.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.watchlist import WatchlistEvent, WatchlistEventType
from ..core.database import SessionLocal
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """Notification payload for WebSocket and push notifications."""
    user_id: str
    symbol: str
    event_type: str
    title: str
    message: str
    score_delta: float
    timestamp: datetime
    event_id: int
    priority: str = "normal"  # "low", "normal", "high"


class NotificationService:
    """Service for handling watchlist monitoring notifications."""
    
    def __init__(self):
        self.redis_channel = "watchlist_notifications"
        self.notification_ttl = 86400  # 24 hours
    
    async def send_monitoring_alert(
        self, 
        watchlist_event: WatchlistEvent
    ) -> bool:
        """
        Send monitoring alert via WebSocket and store for PWA push.
        
        Args:
            watchlist_event: WatchlistEvent database record
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Create notification payload
            payload = NotificationPayload(
                user_id=watchlist_event.user_id,
                symbol=watchlist_event.symbol,
                event_type=watchlist_event.event_type.value,
                title=f"{watchlist_event.symbol} Alert",
                message=watchlist_event.notification_message,
                score_delta=watchlist_event.score_delta,
                timestamp=datetime.now(),
                event_id=watchlist_event.id,
                priority=self._get_notification_priority(watchlist_event)
            )
            
            # Send via WebSocket (Redis pub/sub)
            await self._send_websocket_notification(payload)
            
            # Store for PWA push notification
            await self._store_push_notification(payload)
            
            # Update event record
            await self._mark_notification_sent(watchlist_event.id)
            
            logger.info(f"Sent monitoring alert: {watchlist_event.symbol} - {watchlist_event.event_title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send monitoring alert: {e}")
            return False
    
    async def _send_websocket_notification(self, payload: NotificationPayload) -> None:
        """Send notification via WebSocket (Redis pub/sub)."""
        try:
            # Create WebSocket message
            ws_message = {
                "type": "watchlist_alert",
                "user_id": payload.user_id,
                "data": {
                    "symbol": payload.symbol,
                    "event_type": payload.event_type,
                    "title": payload.title,
                    "message": payload.message,
                    "score_delta": payload.score_delta,
                    "timestamp": payload.timestamp.isoformat(),
                    "event_id": payload.event_id,
                    "priority": payload.priority
                }
            }
            
            # Publish to Redis channel for WebSocket server
            await redis_client.publish(
                self.redis_channel,
                json.dumps(ws_message)
            )
            
            logger.debug(f"Published WebSocket notification for {payload.symbol}")
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
    
    async def _store_push_notification(self, payload: NotificationPayload) -> None:
        """Store notification for PWA push delivery."""
        try:
            # Store in Redis for PWA push service to pick up
            push_key = f"push_notification:{payload.user_id}:{payload.event_id}"
            
            push_data = {
                "title": payload.title,
                "body": payload.message,
                "icon": "/icons/bullsbears-icon-192.png",
                "badge": "/icons/bullsbears-badge-72.png",
                "tag": f"watchlist_{payload.symbol}",
                "data": {
                    "symbol": payload.symbol,
                    "event_type": payload.event_type,
                    "event_id": payload.event_id,
                    "url": f"/watchlist?symbol={payload.symbol}"
                },
                "actions": [
                    {
                        "action": "view",
                        "title": "View Details",
                        "icon": "/icons/view-icon.png"
                    },
                    {
                        "action": "dismiss",
                        "title": "Dismiss",
                        "icon": "/icons/dismiss-icon.png"
                    }
                ],
                "timestamp": payload.timestamp.isoformat(),
                "priority": payload.priority
            }
            
            # Store with TTL
            await redis_client.setex(
                push_key,
                self.notification_ttl,
                json.dumps(push_data)
            )
            
            # Add to user's notification queue
            queue_key = f"notification_queue:{payload.user_id}"
            await redis_client.lpush(queue_key, push_key)
            await redis_client.expire(queue_key, self.notification_ttl)
            
            logger.debug(f"Stored push notification for {payload.symbol}")
            
        except Exception as e:
            logger.error(f"Failed to store push notification: {e}")
    
    async def _mark_notification_sent(self, event_id: int) -> None:
        """Mark watchlist event as notification sent."""
        db = SessionLocal()
        try:
            event = db.query(WatchlistEvent).filter(WatchlistEvent.id == event_id).first()
            if event:
                event.notification_sent = True
                event.notification_sent_at = datetime.now()
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to mark notification sent: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _get_notification_priority(self, event: WatchlistEvent) -> str:
        """Determine notification priority based on event characteristics."""
        # High priority for large score changes or insider activity
        if (abs(event.score_delta) >= 15.0 or 
            event.event_type == WatchlistEventType.INSIDER_ACTIVITY):
            return "high"
        
        # Normal priority for moderate changes
        elif abs(event.score_delta) >= 8.0:
            return "normal"
        
        # Low priority for small changes
        else:
            return "low"
    
    async def get_pending_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending notifications for a user."""
        try:
            queue_key = f"notification_queue:{user_id}"
            
            # Get all notification keys from queue
            notification_keys = await redis_client.lrange(queue_key, 0, -1)
            
            notifications = []
            for key in notification_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
                # Get notification data
                notification_data = await redis_client.get(key)
                if notification_data:
                    try:
                        notification = json.loads(notification_data)
                        notifications.append(notification)
                    except json.JSONDecodeError:
                        continue
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get pending notifications: {e}")
            return []
    
    async def mark_notification_read(self, user_id: str, event_id: int) -> bool:
        """Mark a notification as read and remove from queue."""
        try:
            queue_key = f"notification_queue:{user_id}"
            push_key = f"push_notification:{user_id}:{event_id}"
            
            # Remove from queue
            await redis_client.lrem(queue_key, 1, push_key)
            
            # Delete the notification data
            await redis_client.delete(push_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification read: {e}")
            return False
    
    async def process_pending_alerts(self) -> Dict[str, Any]:
        """
        Process all pending watchlist events that need notifications.
        
        Called by background task to send notifications for new events.
        """
        start_time = datetime.now()
        notifications_sent = 0
        errors = []
        
        db = SessionLocal()
        try:
            # Get unsent notifications from last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            pending_events = db.query(WatchlistEvent).filter(
                and_(
                    WatchlistEvent.notification_sent == False,
                    WatchlistEvent.created_at >= one_hour_ago
                )
            ).all()
            
            logger.info(f"Found {len(pending_events)} pending notifications to process")
            
            for event in pending_events:
                try:
                    success = await self.send_monitoring_alert(event)
                    if success:
                        notifications_sent += 1
                    else:
                        errors.append(f"Failed to send notification for event {event.id}")
                        
                except Exception as e:
                    error_msg = f"Error processing event {event.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": len(errors) == 0,
                "notifications_sent": notifications_sent,
                "total_events_processed": len(pending_events),
                "total_time": total_time,
                "errors": errors
            }
            
            logger.info(f"Notification processing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process pending alerts: {e}")
            return {
                "success": False,
                "error": str(e),
                "notifications_sent": notifications_sent
            }
        finally:
            db.close()


# Global notification service instance
notification_service = NotificationService()
