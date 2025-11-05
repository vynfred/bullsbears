"""
Stock Monitoring Service for Watchlist Items.

Monitors stocks that hit AI picks while on user's watchlist for 7 rolling days.
Triggers alerts for 3 events:
1. Fresh insider buying/selling (>$500k or 3+ filers in 24h)
2. Major 13F change (top-10 holder ±10% QoQ)
3. Macro catalyst (CPI, FOMC, Jobs, Earnings date confirmed)

Reuses existing SEC/FRED/BLS services with zero new infrastructure.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.watchlist import WatchlistEntry, WatchlistEvent, WatchlistEventType
from ..services.sec_data_service import SECDataService
from ..services.fred_data_service import FREDDataService
from ..services.bls_data_service import BLSDataService
from ..core.database import SessionLocal
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


@dataclass
class MonitoringBaseline:
    """Baseline data captured at pick timestamp."""
    symbol: str
    pick_date: datetime
    insider_sentiment: float
    institutional_flow: float
    macro_score: float
    pick_type: str  # 'BULLISH' or 'BEARISH'
    pick_confidence: float


@dataclass
class MonitoringAlert:
    """Alert generated when monitoring threshold is exceeded."""
    symbol: str
    user_id: str
    watchlist_entry_id: int
    event_type: WatchlistEventType
    day_offset: int
    score_delta: float
    baseline_score: float
    current_score: float
    event_title: str
    event_description: str
    event_data: Dict[str, Any]
    pick_date: datetime
    pick_type: str
    pick_confidence: float


class StockMonitoringService:
    """Service for monitoring watchlist stocks that hit AI picks."""
    
    def __init__(self):
        self.sec_service = SECDataService()
        self.fred_service = FREDDataService()
        self.bls_service = BLSDataService()
        
        # Monitoring thresholds
        self.thresholds = {
            "insider_activity": {
                "min_transaction_value": 500000,  # $500k
                "min_filer_count": 3,  # 3+ filers in 24h
                "score_change_threshold": 5.0  # 5% score change
            },
            "institutional_change": {
                "min_position_change": 0.10,  # 10% position change
                "top_holder_rank": 10,  # Top 10 holders only
                "score_change_threshold": 8.0  # 8% score change
            },
            "macro_catalyst": {
                "event_proximity_days": 3,  # Within 3 days of event
                "score_change_threshold": 6.0  # 6% score change
            }
        }
        
        self.cache_ttl = 1800  # 30 minutes cache for monitoring data
    
    async def monitor_watchlist_stocks(self) -> Dict[str, Any]:
        """
        Monitor all active watchlist stocks that are in the 7-day monitoring window.
        
        Returns:
            Dict with monitoring results and alerts generated
        """
        start_time = datetime.now()
        alerts_generated = []
        stocks_monitored = 0
        errors = []
        
        try:
            # Get stocks to monitor
            stocks_to_monitor = await self._get_stocks_to_monitor()
            logger.info(f"Found {len(stocks_to_monitor)} stocks to monitor")
            
            for stock_info in stocks_to_monitor:
                try:
                    # Get baseline data
                    baseline = await self._get_monitoring_baseline(
                        stock_info['symbol'], 
                        stock_info['pick_date']
                    )
                    
                    if not baseline:
                        continue
                    
                    # Check for monitoring events
                    alerts = await self._check_monitoring_events(stock_info, baseline)
                    alerts_generated.extend(alerts)
                    stocks_monitored += 1
                    
                    # Small delay to respect API rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"Error monitoring {stock_info['symbol']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Store alerts in database and send notifications
            if alerts_generated:
                await self._store_monitoring_alerts(alerts_generated)
                await self._send_notifications(alerts_generated)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "stocks_monitored": stocks_monitored,
                "alerts_generated": len(alerts_generated),
                "total_time": total_time,
                "errors": errors,
                "alerts": [
                    {
                        "symbol": alert.symbol,
                        "event_type": alert.event_type.value,
                        "score_delta": alert.score_delta,
                        "event_title": alert.event_title
                    }
                    for alert in alerts_generated
                ]
            }
            
            logger.info(f"Monitoring completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Stock monitoring failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stocks_monitored": stocks_monitored,
                "alerts_generated": len(alerts_generated)
            }
    
    async def _get_stocks_to_monitor(self) -> List[Dict[str, Any]]:
        """Get list of stocks that need monitoring (in 7-day window)."""
        db = SessionLocal()
        try:
            # Calculate 7-day window
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Query watchlist entries that:
            # 1. Are active
            # 2. Have AI picks (confidence > 0)
            # 3. Were added within last 7 days
            # 4. Have pick_date set (from AI recommendation)
            
            query = db.query(WatchlistEntry).filter(
                and_(
                    WatchlistEntry.status == 'ACTIVE',
                    WatchlistEntry.ai_confidence_score > 0,
                    WatchlistEntry.entry_date >= seven_days_ago,
                    WatchlistEntry.created_at.isnot(None)
                )
            )
            
            entries = query.all()
            
            stocks_to_monitor = []
            for entry in entries:
                # Calculate day offset
                day_offset = (datetime.now().date() - entry.entry_date.date()).days
                
                if day_offset < 7:  # Still in monitoring window
                    stocks_to_monitor.append({
                        'watchlist_entry_id': entry.id,
                        'symbol': entry.symbol,
                        'user_id': f"user_{entry.id % 1000}",  # Anonymous user ID
                        'pick_date': entry.entry_date,
                        'pick_type': entry.ai_recommendation or 'BULLISH',
                        'pick_confidence': entry.ai_confidence_score,
                        'day_offset': day_offset
                    })
            
            return stocks_to_monitor
            
        finally:
            db.close()
    
    async def _get_monitoring_baseline(
        self, 
        symbol: str, 
        pick_date: datetime
    ) -> Optional[MonitoringBaseline]:
        """Get or create baseline data for monitoring."""
        cache_key = f"monitoring_baseline:{symbol}:{pick_date.date()}"
        
        # Check cache first
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                data['pick_date'] = datetime.fromisoformat(data['pick_date'])
                return MonitoringBaseline(**data)
            except Exception as e:
                logger.warning(f"Failed to parse cached baseline: {e}")
        
        try:
            # Generate baseline using existing services
            insider_data = await self.sec_service.get_insider_sentiment_score(symbol, days_back=30)
            institutional_data = await self.sec_service.get_institutional_flow_score(symbol)
            macro_data = await self.fred_service.get_economic_snapshot()
            
            baseline = MonitoringBaseline(
                symbol=symbol,
                pick_date=pick_date,
                insider_sentiment=insider_data.get('sentiment_score', 0.0),
                institutional_flow=institutional_data.get('flow_score', 0.0),
                macro_score=macro_data.get('market_sentiment_score', 0.0),
                pick_type='BULLISH',  # Default, will be updated from watchlist
                pick_confidence=0.0   # Default, will be updated from watchlist
            )
            
            # Cache the baseline
            baseline_dict = baseline.__dict__.copy()
            baseline_dict['pick_date'] = baseline.pick_date.isoformat()
            
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(baseline_dict)
            )
            
            return baseline
            
        except Exception as e:
            logger.error(f"Failed to get monitoring baseline for {symbol}: {e}")
            return None
    
    async def _check_monitoring_events(
        self, 
        stock_info: Dict[str, Any], 
        baseline: MonitoringBaseline
    ) -> List[MonitoringAlert]:
        """Check for monitoring events that exceed thresholds."""
        alerts = []
        symbol = stock_info['symbol']
        
        try:
            # Check 1: Fresh insider activity
            insider_alert = await self._check_insider_activity(stock_info, baseline)
            if insider_alert:
                alerts.append(insider_alert)
            
            # Check 2: Major institutional changes
            institutional_alert = await self._check_institutional_changes(stock_info, baseline)
            if institutional_alert:
                alerts.append(institutional_alert)
            
            # Check 3: Macro catalysts
            macro_alert = await self._check_macro_catalysts(stock_info, baseline)
            if macro_alert:
                alerts.append(macro_alert)
                
        except Exception as e:
            logger.error(f"Error checking monitoring events for {symbol}: {e}")
        
        return alerts

    async def _check_insider_activity(
        self,
        stock_info: Dict[str, Any],
        baseline: MonitoringBaseline
    ) -> Optional[MonitoringAlert]:
        """Check for fresh insider buying/selling activity."""
        try:
            symbol = stock_info['symbol']

            # Get recent insider activity (last 24 hours)
            insider_data = await self.sec_service.get_recent_insider_activity(
                symbol,
                hours_back=24
            )

            if not insider_data:
                return None

            total_value = insider_data.get('total_transaction_value', 0)
            filer_count = insider_data.get('unique_filer_count', 0)
            net_sentiment = insider_data.get('net_sentiment_score', 0.0)

            # Check thresholds
            threshold = self.thresholds['insider_activity']
            if (total_value >= threshold['min_transaction_value'] or
                filer_count >= threshold['min_filer_count']):

                # Calculate score delta
                current_score = baseline.insider_sentiment + (net_sentiment * 10)  # Scale sentiment
                score_delta = current_score - baseline.insider_sentiment

                if abs(score_delta) >= threshold['score_change_threshold']:
                    # Generate event title
                    if total_value >= threshold['min_transaction_value']:
                        event_title = f"{filer_count} exec{'s' if filer_count > 1 else ''} just {'bought' if net_sentiment > 0 else 'sold'} ${total_value/1000000:.1f}M"
                    else:
                        event_title = f"{filer_count} execs just made significant trades"

                    return MonitoringAlert(
                        symbol=symbol,
                        user_id=stock_info['user_id'],
                        watchlist_entry_id=stock_info['watchlist_entry_id'],
                        event_type=WatchlistEventType.INSIDER_ACTIVITY,
                        day_offset=stock_info['day_offset'],
                        score_delta=score_delta,
                        baseline_score=baseline.insider_sentiment,
                        current_score=current_score,
                        event_title=event_title,
                        event_description=f"Recent insider activity: {filer_count} filers, ${total_value:,.0f} total value",
                        event_data=insider_data,
                        pick_date=stock_info['pick_date'],
                        pick_type=stock_info['pick_type'],
                        pick_confidence=stock_info['pick_confidence']
                    )

            return None

        except Exception as e:
            logger.error(f"Error checking insider activity for {stock_info['symbol']}: {e}")
            return None

    async def _check_institutional_changes(
        self,
        stock_info: Dict[str, Any],
        baseline: MonitoringBaseline
    ) -> Optional[MonitoringAlert]:
        """Check for major 13F institutional changes."""
        try:
            symbol = stock_info['symbol']

            # Get recent institutional changes
            institutional_data = await self.sec_service.get_recent_institutional_changes(
                symbol,
                days_back=90  # Quarterly data
            )

            if not institutional_data:
                return None

            # Check for top-10 holder changes ±10% QoQ
            significant_changes = institutional_data.get('significant_changes', [])
            threshold = self.thresholds['institutional_change']

            for change in significant_changes:
                if (change.get('holder_rank', 999) <= threshold['top_holder_rank'] and
                    abs(change.get('position_change_percent', 0)) >= threshold['min_position_change'] * 100):

                    # Calculate score delta
                    flow_impact = change.get('position_change_percent', 0) / 100 * 5  # Scale to score
                    current_score = baseline.institutional_flow + flow_impact
                    score_delta = current_score - baseline.institutional_flow

                    if abs(score_delta) >= threshold['score_change_threshold']:
                        # Generate event title
                        holder_name = change.get('holder_name', 'Major institution')
                        change_pct = change.get('position_change_percent', 0)
                        action = 'increased' if change_pct > 0 else 'decreased'

                        event_title = f"{holder_name} {action} position by {abs(change_pct):.0f}%"

                        return MonitoringAlert(
                            symbol=symbol,
                            user_id=stock_info['user_id'],
                            watchlist_entry_id=stock_info['watchlist_entry_id'],
                            event_type=WatchlistEventType.INSTITUTIONAL_CHANGE,
                            day_offset=stock_info['day_offset'],
                            score_delta=score_delta,
                            baseline_score=baseline.institutional_flow,
                            current_score=current_score,
                            event_title=event_title,
                            event_description=f"13F filing shows {holder_name} {action} position by {abs(change_pct):.1f}%",
                            event_data=change,
                            pick_date=stock_info['pick_date'],
                            pick_type=stock_info['pick_type'],
                            pick_confidence=stock_info['pick_confidence']
                        )

            return None

        except Exception as e:
            logger.error(f"Error checking institutional changes for {stock_info['symbol']}: {e}")
            return None

    async def _check_macro_catalysts(
        self,
        stock_info: Dict[str, Any],
        baseline: MonitoringBaseline
    ) -> Optional[MonitoringAlert]:
        """Check for macro economic catalysts."""
        try:
            symbol = stock_info['symbol']

            # Get upcoming economic events
            fred_events = await self.fred_service.get_upcoming_economic_events(days_ahead=7)
            bls_events = await self.bls_service.get_upcoming_releases(days_ahead=7)

            # Combine events
            all_events = []
            if fred_events:
                all_events.extend(fred_events.get('events', []))
            if bls_events:
                all_events.extend(bls_events.get('releases', []))

            threshold = self.thresholds['macro_catalyst']

            for event in all_events:
                event_date = event.get('date')
                if not event_date:
                    continue

                # Check if event is within proximity threshold
                if isinstance(event_date, str):
                    event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))

                days_until_event = (event_date.date() - datetime.now().date()).days

                if 0 <= days_until_event <= threshold['event_proximity_days']:
                    # Calculate impact on macro score
                    event_impact = event.get('market_impact_score', 0.0)
                    current_score = baseline.macro_score + event_impact
                    score_delta = current_score - baseline.macro_score

                    if abs(score_delta) >= threshold['score_change_threshold']:
                        event_name = event.get('name', 'Economic event')
                        event_title = f"{event_name} in {days_until_event} day{'s' if days_until_event != 1 else ''}"

                        return MonitoringAlert(
                            symbol=symbol,
                            user_id=stock_info['user_id'],
                            watchlist_entry_id=stock_info['watchlist_entry_id'],
                            event_type=WatchlistEventType.MACRO_CATALYST,
                            day_offset=stock_info['day_offset'],
                            score_delta=score_delta,
                            baseline_score=baseline.macro_score,
                            current_score=current_score,
                            event_title=event_title,
                            event_description=f"Upcoming {event_name} on {event_date.strftime('%Y-%m-%d')}",
                            event_data=event,
                            pick_date=stock_info['pick_date'],
                            pick_type=stock_info['pick_type'],
                            pick_confidence=stock_info['pick_confidence']
                        )

            return None

        except Exception as e:
            logger.error(f"Error checking macro catalysts for {stock_info['symbol']}: {e}")
            return None

    async def _store_monitoring_alerts(self, alerts: List[MonitoringAlert]) -> None:
        """Store monitoring alerts in the database."""
        if not alerts:
            return

        db = SessionLocal()
        try:
            for alert in alerts:
                # Check if similar alert already exists (avoid duplicates)
                existing = db.query(WatchlistEvent).filter(
                    and_(
                        WatchlistEvent.symbol == alert.symbol,
                        WatchlistEvent.user_id == alert.user_id,
                        WatchlistEvent.event_type == alert.event_type,
                        WatchlistEvent.day_offset == alert.day_offset,
                        WatchlistEvent.created_at >= datetime.now() - timedelta(hours=1)
                    )
                ).first()

                if existing:
                    logger.info(f"Similar alert already exists for {alert.symbol}, skipping")
                    continue

                # Create new event record
                event = WatchlistEvent(
                    watchlist_entry_id=alert.watchlist_entry_id,
                    symbol=alert.symbol,
                    user_id=alert.user_id,
                    event_type=alert.event_type,
                    day_offset=alert.day_offset,
                    score_delta=alert.score_delta,
                    baseline_score=alert.baseline_score,
                    current_score=alert.current_score,
                    event_title=alert.event_title,
                    event_description=alert.event_description,
                    event_data=alert.event_data,
                    pick_date=alert.pick_date,
                    pick_type=alert.pick_type,
                    pick_confidence=alert.pick_confidence,
                    notification_sent=False
                )

                db.add(event)
                logger.info(f"Stored monitoring alert: {alert.symbol} - {alert.event_title}")

            db.commit()

        except Exception as e:
            logger.error(f"Error storing monitoring alerts: {e}")
            db.rollback()
        finally:
            db.close()

    async def _send_notifications(self, alerts: List[MonitoringAlert]) -> None:
        """Send notifications for monitoring alerts."""
        if not alerts:
            return

        try:
            from .notification_service import notification_service

            # Get the database records for the alerts
            db = SessionLocal()
            try:
                for alert in alerts:
                    # Find the corresponding database record
                    event = db.query(WatchlistEvent).filter(
                        and_(
                            WatchlistEvent.symbol == alert.symbol,
                            WatchlistEvent.user_id == alert.user_id,
                            WatchlistEvent.event_type == alert.event_type,
                            WatchlistEvent.day_offset == alert.day_offset,
                            WatchlistEvent.notification_sent == False
                        )
                    ).first()

                    if event:
                        # Send notification
                        success = await notification_service.send_monitoring_alert(event)
                        if success:
                            logger.info(f"Sent notification for {alert.symbol} - {alert.event_title}")
                        else:
                            logger.warning(f"Failed to send notification for {alert.symbol}")
                    else:
                        logger.warning(f"Could not find database record for alert: {alert.symbol}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
