"""
Watchlist Notifications Service for BullsBears.xyz
Handles target hit notifications, stop loss alerts, and performance tracking notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.watchlist import WatchlistEntry, WatchlistPriceHistory
from ..core.database import get_db
from ..services.stock_data import StockDataService

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    TARGET_HIT = "target_hit"
    STOP_LOSS_HIT = "stop_loss_hit"
    PRICE_ALERT = "price_alert"
    PERFORMANCE_MILESTONE = "performance_milestone"
    DAILY_SUMMARY = "daily_summary"


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class WatchlistNotification:
    """Notification for watchlist events."""
    id: str
    entry_id: int
    symbol: str
    notification_type: NotificationType
    severity: AlertSeverity
    title: str
    message: str
    current_price: float
    entry_price: float
    target_price: Optional[float]
    stop_loss_price: Optional[float]
    gain_percent: float
    gain_dollars: float
    timestamp: datetime
    metadata: Dict[str, Any]


class WatchlistNotificationService:
    """Service for managing watchlist notifications and alerts."""
    
    def __init__(self):
        self.stock_data_service = StockDataService()
        
        # Notification thresholds
        self.performance_milestones = [5, 10, 15, 20, 25, 30, 50, 75, 100]  # Percentage gains
        self.loss_thresholds = [-5, -10, -15, -20, -25, -30]  # Percentage losses
        
    async def check_all_watchlist_alerts(self, db: Session) -> List[WatchlistNotification]:
        """Check all active watchlist entries for alert conditions."""
        notifications = []
        
        try:
            # Get all active watchlist entries
            active_entries = db.query(WatchlistEntry).filter(
                WatchlistEntry.status == 'ACTIVE'
            ).all()
            
            for entry in active_entries:
                entry_notifications = await self._check_entry_alerts(db, entry)
                notifications.extend(entry_notifications)
            
            # Store notifications in database (if we had a notifications table)
            for notification in notifications:
                await self._store_notification(db, notification)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error checking watchlist alerts: {e}")
            return []
    
    async def _check_entry_alerts(self, db: Session, entry: WatchlistEntry) -> List[WatchlistNotification]:
        """Check a single watchlist entry for alert conditions."""
        notifications = []
        
        try:
            # Get current price
            current_price = await self.stock_data_service.get_current_price(entry.symbol)
            if not current_price:
                return notifications
            
            # Calculate performance metrics
            gain_percent = ((current_price - entry.entry_price) / entry.entry_price) * 100
            gain_dollars = (current_price - entry.entry_price) * (entry.position_size_dollars / entry.entry_price)
            
            # Check target hit
            if entry.target_price and current_price >= entry.target_price:
                notifications.append(self._create_target_hit_notification(
                    entry, current_price, gain_percent, gain_dollars
                ))
            
            # Check stop loss hit
            if entry.stop_loss_price and current_price <= entry.stop_loss_price:
                notifications.append(self._create_stop_loss_notification(
                    entry, current_price, gain_percent, gain_dollars
                ))
            
            # Check performance milestones
            milestone_notifications = self._check_performance_milestones(
                entry, current_price, gain_percent, gain_dollars
            )
            notifications.extend(milestone_notifications)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error checking alerts for entry {entry.id}: {e}")
            return []
    
    def _create_target_hit_notification(self, entry: WatchlistEntry, current_price: float, 
                                      gain_percent: float, gain_dollars: float) -> WatchlistNotification:
        """Create a target hit notification."""
        return WatchlistNotification(
            id=f"target_hit_{entry.id}_{datetime.now().timestamp()}",
            entry_id=entry.id,
            symbol=entry.symbol,
            notification_type=NotificationType.TARGET_HIT,
            severity=AlertSeverity.HIGH,
            title=f"🎯 Target Hit: {entry.symbol}",
            message=f"{entry.symbol} hit your target price of ${entry.target_price:.2f}! Current: ${current_price:.2f} (+{gain_percent:.1f}%)",
            current_price=current_price,
            entry_price=entry.entry_price,
            target_price=entry.target_price,
            stop_loss_price=entry.stop_loss_price,
            gain_percent=gain_percent,
            gain_dollars=gain_dollars,
            timestamp=datetime.now(),
            metadata={
                "ai_confidence": entry.ai_confidence_score,
                "days_held": (datetime.now() - entry.entry_date).days,
                "recommendation": entry.ai_recommendation
            }
        )
    
    def _create_stop_loss_notification(self, entry: WatchlistEntry, current_price: float,
                                     gain_percent: float, gain_dollars: float) -> WatchlistNotification:
        """Create a stop loss hit notification."""
        return WatchlistNotification(
            id=f"stop_loss_{entry.id}_{datetime.now().timestamp()}",
            entry_id=entry.id,
            symbol=entry.symbol,
            notification_type=NotificationType.STOP_LOSS_HIT,
            severity=AlertSeverity.CRITICAL,
            title=f"🛑 Stop Loss Hit: {entry.symbol}",
            message=f"{entry.symbol} hit your stop loss of ${entry.stop_loss_price:.2f}. Current: ${current_price:.2f} ({gain_percent:.1f}%)",
            current_price=current_price,
            entry_price=entry.entry_price,
            target_price=entry.target_price,
            stop_loss_price=entry.stop_loss_price,
            gain_percent=gain_percent,
            gain_dollars=gain_dollars,
            timestamp=datetime.now(),
            metadata={
                "ai_confidence": entry.ai_confidence_score,
                "days_held": (datetime.now() - entry.entry_date).days,
                "recommendation": entry.ai_recommendation
            }
        )
    
    def _check_performance_milestones(self, entry: WatchlistEntry, current_price: float,
                                    gain_percent: float, gain_dollars: float) -> List[WatchlistNotification]:
        """Check for performance milestone notifications."""
        notifications = []
        
        # Check positive milestones
        for milestone in self.performance_milestones:
            if gain_percent >= milestone:
                # Check if we've already sent this milestone notification
                if not self._milestone_already_sent(entry.id, milestone):
                    notifications.append(self._create_milestone_notification(
                        entry, current_price, gain_percent, gain_dollars, milestone, positive=True
                    ))
        
        # Check negative thresholds
        for threshold in self.loss_thresholds:
            if gain_percent <= threshold:
                if not self._milestone_already_sent(entry.id, threshold):
                    notifications.append(self._create_milestone_notification(
                        entry, current_price, gain_percent, gain_dollars, threshold, positive=False
                    ))
        
        return notifications
    
    def _create_milestone_notification(self, entry: WatchlistEntry, current_price: float,
                                     gain_percent: float, gain_dollars: float, 
                                     milestone: float, positive: bool) -> WatchlistNotification:
        """Create a performance milestone notification."""
        if positive:
            emoji = "🚀" if milestone >= 20 else "📈"
            title = f"{emoji} {entry.symbol} +{milestone}%!"
            severity = AlertSeverity.HIGH if milestone >= 20 else AlertSeverity.MEDIUM
        else:
            emoji = "📉"
            title = f"{emoji} {entry.symbol} {milestone}%"
            severity = AlertSeverity.MEDIUM if milestone >= -10 else AlertSeverity.HIGH
        
        return WatchlistNotification(
            id=f"milestone_{entry.id}_{milestone}_{datetime.now().timestamp()}",
            entry_id=entry.id,
            symbol=entry.symbol,
            notification_type=NotificationType.PERFORMANCE_MILESTONE,
            severity=severity,
            title=title,
            message=f"{entry.symbol} reached {gain_percent:.1f}% gain. Current: ${current_price:.2f}",
            current_price=current_price,
            entry_price=entry.entry_price,
            target_price=entry.target_price,
            stop_loss_price=entry.stop_loss_price,
            gain_percent=gain_percent,
            gain_dollars=gain_dollars,
            timestamp=datetime.now(),
            metadata={
                "milestone": milestone,
                "ai_confidence": entry.ai_confidence_score,
                "days_held": (datetime.now() - entry.entry_date).days
            }
        )
    
    def _milestone_already_sent(self, entry_id: int, milestone: float) -> bool:
        """Check if a milestone notification was already sent for this entry."""
        # This would check a notifications table in a real implementation
        # For now, return False to allow all notifications
        return False
    
    async def _store_notification(self, db: Session, notification: WatchlistNotification):
        """Store notification in database (placeholder for future implementation)."""
        # This would store the notification in a dedicated table
        logger.info(f"Notification: {notification.title} - {notification.message}")
    
    async def generate_daily_summary(self, db: Session) -> Optional[WatchlistNotification]:
        """Generate a daily performance summary notification."""
        try:
            # Get all active entries
            active_entries = db.query(WatchlistEntry).filter(
                WatchlistEntry.status == 'ACTIVE'
            ).all()
            
            if not active_entries:
                return None
            
            total_entries = len(active_entries)
            winners = 0
            losers = 0
            total_gain_percent = 0
            total_gain_dollars = 0
            
            for entry in active_entries:
                current_price = await self.stock_data_service.get_current_price(entry.symbol)
                if current_price:
                    gain_percent = ((current_price - entry.entry_price) / entry.entry_price) * 100
                    gain_dollars = (current_price - entry.entry_price) * (entry.position_size_dollars / entry.entry_price)
                    
                    total_gain_percent += gain_percent
                    total_gain_dollars += gain_dollars
                    
                    if gain_percent > 0:
                        winners += 1
                    elif gain_percent < 0:
                        losers += 1
            
            avg_gain_percent = total_gain_percent / total_entries if total_entries > 0 else 0
            
            return WatchlistNotification(
                id=f"daily_summary_{datetime.now().strftime('%Y%m%d')}",
                entry_id=0,  # Summary notification
                symbol="PORTFOLIO",
                notification_type=NotificationType.DAILY_SUMMARY,
                severity=AlertSeverity.LOW,
                title="📊 Daily Watchlist Summary",
                message=f"Portfolio: {winners}W/{losers}L, Avg: {avg_gain_percent:.1f}%, Total: ${total_gain_dollars:.2f}",
                current_price=0,
                entry_price=0,
                target_price=None,
                stop_loss_price=None,
                gain_percent=avg_gain_percent,
                gain_dollars=total_gain_dollars,
                timestamp=datetime.now(),
                metadata={
                    "total_entries": total_entries,
                    "winners": winners,
                    "losers": losers,
                    "neutral": total_entries - winners - losers
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return None
