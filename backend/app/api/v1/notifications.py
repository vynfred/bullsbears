"""
Notifications API endpoints for watchlist monitoring alerts.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from ...core.database import get_db
from ...models.watchlist import WatchlistEvent, WatchlistEventType
from ...services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/pending/{user_id}")
async def get_pending_notifications(
    user_id: str,
    limit: int = Query(default=20, le=100, description="Maximum number of notifications to return")
) -> Dict[str, Any]:
    """
    Get pending notifications for a user.
    
    Args:
        user_id: Anonymous user ID
        limit: Maximum number of notifications to return
        
    Returns:
        Dict with pending notifications
    """
    try:
        notifications = await notification_service.get_pending_notifications(user_id)
        
        # Limit results
        limited_notifications = notifications[:limit]
        
        return {
            "success": True,
            "user_id": user_id,
            "notifications": limited_notifications,
            "total_count": len(notifications),
            "returned_count": len(limited_notifications),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting pending notifications for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-read/{user_id}/{event_id}")
async def mark_notification_read(
    user_id: str,
    event_id: int
) -> Dict[str, Any]:
    """
    Mark a notification as read.
    
    Args:
        user_id: Anonymous user ID
        event_id: Watchlist event ID
        
    Returns:
        Success status
    """
    try:
        success = await notification_service.mark_notification_read(user_id, event_id)
        
        return {
            "success": success,
            "user_id": user_id,
            "event_id": event_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_notification_history(
    user_id: str,
    days_back: int = Query(default=7, le=30, description="Days to look back for notifications"),
    event_type: str = Query(default=None, description="Filter by event type"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get notification history for a user.
    
    Args:
        user_id: Anonymous user ID
        days_back: Number of days to look back
        event_type: Optional event type filter
        db: Database session
        
    Returns:
        Dict with notification history
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Build query
        query = db.query(WatchlistEvent).filter(
            and_(
                WatchlistEvent.user_id == user_id,
                WatchlistEvent.created_at >= start_date,
                WatchlistEvent.created_at <= end_date
            )
        )
        
        # Add event type filter if specified
        if event_type:
            try:
                event_type_enum = WatchlistEventType(event_type)
                query = query.filter(WatchlistEvent.event_type == event_type_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        # Order by most recent first
        events = query.order_by(desc(WatchlistEvent.created_at)).all()
        
        # Format response
        notifications = []
        for event in events:
            notifications.append({
                "id": event.id,
                "symbol": event.symbol,
                "event_type": event.event_type.value,
                "event_title": event.event_title,
                "event_description": event.event_description,
                "score_delta": event.score_delta,
                "baseline_score": event.baseline_score,
                "current_score": event.current_score,
                "day_offset": event.day_offset,
                "pick_date": event.pick_date.isoformat(),
                "pick_type": event.pick_type,
                "pick_confidence": event.pick_confidence,
                "notification_sent": event.notification_sent,
                "notification_sent_at": event.notification_sent_at.isoformat() if event.notification_sent_at else None,
                "created_at": event.created_at.isoformat(),
                "notification_message": event.notification_message
            })
        
        return {
            "success": True,
            "user_id": user_id,
            "notifications": notifications,
            "total_count": len(notifications),
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days_back": days_back
            },
            "filters": {
                "event_type": event_type
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{user_id}")
async def get_notification_stats(
    user_id: str,
    days_back: int = Query(default=30, le=90, description="Days to look back for stats"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get notification statistics for a user.
    
    Args:
        user_id: Anonymous user ID
        days_back: Number of days to look back
        db: Database session
        
    Returns:
        Dict with notification statistics
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get all events for the user in the date range
        events = db.query(WatchlistEvent).filter(
            and_(
                WatchlistEvent.user_id == user_id,
                WatchlistEvent.created_at >= start_date,
                WatchlistEvent.created_at <= end_date
            )
        ).all()
        
        # Calculate statistics
        total_notifications = len(events)
        notifications_sent = sum(1 for event in events if event.notification_sent)
        
        # Group by event type
        event_type_counts = {}
        for event in events:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        # Group by symbol
        symbol_counts = {}
        for event in events:
            symbol = event.symbol
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        # Calculate average score delta
        score_deltas = [abs(event.score_delta) for event in events]
        avg_score_delta = sum(score_deltas) / len(score_deltas) if score_deltas else 0.0
        
        # Get top symbols by notification count
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "success": True,
            "user_id": user_id,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days_back": days_back
            },
            "statistics": {
                "total_notifications": total_notifications,
                "notifications_sent": notifications_sent,
                "notification_delivery_rate": notifications_sent / max(total_notifications, 1),
                "average_score_delta": round(avg_score_delta, 2),
                "event_type_breakdown": event_type_counts,
                "top_symbols": [{"symbol": symbol, "count": count} for symbol, count in top_symbols]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting notification stats for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/{user_id}")
async def send_test_notification(
    user_id: str,
    symbol: str = Query(default="TSLA", description="Symbol for test notification")
) -> Dict[str, Any]:
    """
    Send a test notification (development/testing only).
    
    Args:
        user_id: Anonymous user ID
        symbol: Stock symbol for test
        
    Returns:
        Success status
    """
    try:
        # Create test notification payload
        from ...services.notification_service import NotificationPayload
        
        test_payload = NotificationPayload(
            user_id=user_id,
            symbol=symbol,
            event_type="insider_activity",
            title=f"{symbol} Test Alert",
            message=f"{symbol}: 3 execs just bought $4.2M — Bullish Indication score ↑ 12%",
            score_delta=12.0,
            timestamp=datetime.now(),
            event_id=999999,  # Test event ID
            priority="normal"
        )
        
        # Send via WebSocket
        await notification_service._send_websocket_notification(test_payload)
        
        # Store for PWA push
        await notification_service._store_push_notification(test_payload)
        
        return {
            "success": True,
            "message": "Test notification sent",
            "user_id": user_id,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
