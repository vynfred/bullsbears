"""
Real-time Price Monitoring Service
Monitors picks and watchlist items for price changes, target hits, and alerts during market hours.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.database import get_db
from ..models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from ..models.watchlist import WatchlistEntry
from ..services.stock_data import StockDataService
from ..services.watchlist_notifications import WatchlistNotificationService
from ..core.redis_client import redis_client
from ..websocket.manager import manager

logger = logging.getLogger(__name__)


class RealtimePriceMonitor:
    """Real-time price monitoring for picks and watchlist items"""
    
    def __init__(self):
        self.stock_data_service = StockDataService()
        self.notification_service = WatchlistNotificationService()
        self.redis_client = redis_client
        self.is_monitoring = False
        self.monitored_symbols: Set[str] = set()
        
    def is_market_hours(self) -> bool:
        """Check if it's currently market hours (9:30 AM - 4:00 PM ET, Mon-Fri)"""
        now = datetime.utcnow()
        # Convert to ET (approximate, doesn't handle DST perfectly)
        et_hour = (now.hour - 5) % 24
        et_minute = now.minute
        is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
        
        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = et_hour > 9 or (et_hour == 9 and et_minute >= 30)
        market_close = et_hour < 16
        
        return is_weekday and market_open and market_close
    
    async def start_monitoring(self, db: Session) -> Dict:
        """Start real-time price monitoring"""
        if self.is_monitoring:
            return {"status": "already_running"}
        
        logger.info("🚀 Starting real-time price monitoring")
        self.is_monitoring = True
        
        # Get symbols to monitor
        symbols_to_monitor = await self._get_symbols_to_monitor(db)
        self.monitored_symbols = set(symbols_to_monitor)
        
        logger.info(f"📊 Monitoring {len(self.monitored_symbols)} symbols: {list(self.monitored_symbols)[:10]}...")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop(db))
        
        return {
            "status": "started",
            "symbols_count": len(self.monitored_symbols),
            "symbols": list(self.monitored_symbols)
        }
    
    async def stop_monitoring(self) -> Dict:
        """Stop real-time price monitoring"""
        logger.info("🛑 Stopping real-time price monitoring")
        self.is_monitoring = False
        self.monitored_symbols.clear()
        
        return {"status": "stopped"}
    
    async def _monitoring_loop(self, db: Session):
        """Main monitoring loop - runs every 30 seconds during market hours"""
        
        while self.is_monitoring:
            try:
                # Only monitor during market hours
                if not self.is_market_hours():
                    logger.info("Outside market hours, pausing monitoring")
                    await asyncio.sleep(300)  # Check again in 5 minutes
                    continue
                
                # Update monitored symbols list
                current_symbols = await self._get_symbols_to_monitor(db)
                self.monitored_symbols = set(current_symbols)
                
                # Monitor each symbol
                monitoring_results = await self._monitor_all_symbols(db)
                
                # Log results
                if monitoring_results["alerts_triggered"] > 0:
                    logger.info(f"🚨 Monitoring cycle complete: {monitoring_results}")
                
                # Wait 30 seconds before next cycle (real-time monitoring)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"💥 Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _get_symbols_to_monitor(self, db: Session) -> List[str]:
        """Get list of symbols that need real-time monitoring"""
        
        symbols = set()
        
        # Get symbols from active picks (last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        active_picks = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.alert_outcome == AlertOutcome.PENDING,
                AnalysisResult.timestamp >= cutoff_date,
                AnalysisResult.alert_type.in_([AlertType.BULLISH, AlertType.BEARISH])
            )
        ).all()
        
        for pick in active_picks:
            symbols.add(pick.symbol)
        
        # Get symbols from active watchlist entries
        active_watchlist = db.query(WatchlistEntry).filter(
            WatchlistEntry.status == 'ACTIVE'
        ).all()
        
        for entry in active_watchlist:
            symbols.add(entry.symbol)
        
        return list(symbols)
    
    async def _monitor_all_symbols(self, db: Session) -> Dict:
        """Monitor all symbols for price changes and alerts"""
        
        results = {
            "symbols_monitored": 0,
            "price_updates": 0,
            "alerts_triggered": 0,
            "websocket_updates": 0,
            "errors": 0
        }
        
        # Process symbols in batches to avoid overwhelming APIs
        batch_size = 10
        symbol_list = list(self.monitored_symbols)
        
        for i in range(0, len(symbol_list), batch_size):
            batch = symbol_list[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [self._monitor_symbol(db, symbol) for symbol in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Aggregate results
            for result in batch_results:
                if isinstance(result, Exception):
                    results["errors"] += 1
                    logger.error(f"Symbol monitoring error: {result}")
                elif isinstance(result, dict):
                    results["symbols_monitored"] += 1
                    if result.get("price_updated"):
                        results["price_updates"] += 1
                    if result.get("alert_triggered"):
                        results["alerts_triggered"] += 1
                    if result.get("websocket_sent"):
                        results["websocket_updates"] += 1
            
            # Small delay between batches to respect rate limits
            await asyncio.sleep(2)
        
        return results
    
    async def _monitor_symbol(self, db: Session, symbol: str) -> Dict:
        """Monitor a single symbol for price changes and alerts"""
        
        result = {
            "symbol": symbol,
            "price_updated": False,
            "alert_triggered": False,
            "websocket_sent": False
        }
        
        try:
            # Get current price
            quote_data = await self.stock_data_service.get_real_time_quote(symbol)
            if not quote_data:
                return result
            
            current_price = quote_data.get('price', 0)
            if current_price <= 0:
                return result
            
            # Update picks
            await self._update_picks_prices(db, symbol, current_price, quote_data)
            
            # Update watchlist entries
            await self._update_watchlist_prices(db, symbol, current_price, quote_data)
            
            # Check for alerts
            alerts = await self._check_price_alerts(db, symbol, current_price, quote_data)
            if alerts:
                result["alert_triggered"] = True
                # Send notifications for alerts
                for alert in alerts:
                    await self.notification_service.send_price_alert(alert)
            
            # Send WebSocket update
            await self._send_websocket_update(symbol, quote_data)
            result["websocket_sent"] = True
            
            result["price_updated"] = True
            
        except Exception as e:
            logger.error(f"Error monitoring {symbol}: {e}")
            raise e
        
        return result
    
    async def _update_picks_prices(self, db: Session, symbol: str, current_price: float, quote_data: Dict):
        """Update current prices for picks"""
        
        # Get active picks for this symbol
        active_picks = db.query(AnalysisResult).filter(
            and_(
                AnalysisResult.symbol == symbol,
                AnalysisResult.alert_outcome == AlertOutcome.PENDING,
                AnalysisResult.alert_type.in_([AlertType.BULLISH, AlertType.BEARISH])
            )
        ).all()
        
        for pick in active_picks:
            # Update current price (store in a custom field or use existing)
            # Note: AnalysisResult doesn't have current_price field, so we'll cache it
            cache_key = f"pick_price:{pick.id}"
            await self.redis_client.cache_with_ttl(cache_key, {
                "current_price": current_price,
                "quote_data": quote_data,
                "updated_at": datetime.now().isoformat()
            }, 300)  # 5 minute cache
        
        if active_picks:
            db.commit()
    
    async def _update_watchlist_prices(self, db: Session, symbol: str, current_price: float, quote_data: Dict):
        """Update current prices for watchlist entries"""
        
        # Get active watchlist entries for this symbol
        active_entries = db.query(WatchlistEntry).filter(
            and_(
                WatchlistEntry.symbol == symbol,
                WatchlistEntry.status == 'ACTIVE'
            )
        ).all()
        
        for entry in active_entries:
            # Calculate performance metrics
            entry_price = entry.entry_price
            return_percent = ((current_price - entry_price) / entry_price) * 100
            return_dollars = (current_price - entry_price) * (entry.position_size_shares or 1)
            
            # Update entry
            entry.current_price = current_price
            entry.current_return_percent = return_percent
            entry.current_return_dollars = return_dollars
            entry.last_price_update = datetime.now()
            entry.price_update_count = (entry.price_update_count or 0) + 1
        
        if active_entries:
            db.commit()
    
    async def _check_price_alerts(self, db: Session, symbol: str, current_price: float, quote_data: Dict) -> List[Dict]:
        """Check for price-based alerts (target hits, stop losses, etc.)"""
        
        alerts = []
        
        # Check watchlist entries for target/stop loss hits
        active_entries = db.query(WatchlistEntry).filter(
            and_(
                WatchlistEntry.symbol == symbol,
                WatchlistEntry.status == 'ACTIVE'
            )
        ).all()
        
        for entry in active_entries:
            # Check target hit
            if entry.target_price and current_price >= entry.target_price:
                alerts.append({
                    "type": "target_hit",
                    "symbol": symbol,
                    "entry_id": entry.id,
                    "current_price": current_price,
                    "target_price": entry.target_price,
                    "gain_percent": ((current_price - entry.entry_price) / entry.entry_price) * 100,
                    "message": f"🎯 {symbol} hit target ${entry.target_price:.2f}! Current: ${current_price:.2f}"
                })
            
            # Check stop loss hit
            if entry.stop_loss_price and current_price <= entry.stop_loss_price:
                alerts.append({
                    "type": "stop_loss",
                    "symbol": symbol,
                    "entry_id": entry.id,
                    "current_price": current_price,
                    "stop_loss_price": entry.stop_loss_price,
                    "loss_percent": ((current_price - entry.entry_price) / entry.entry_price) * 100,
                    "message": f"🛑 {symbol} hit stop loss ${entry.stop_loss_price:.2f}! Current: ${current_price:.2f}"
                })
            
            # Check for significant moves (>5% in either direction)
            if entry.current_return_percent:
                if abs(entry.current_return_percent) >= 5.0:
                    direction = "📈" if entry.current_return_percent > 0 else "📉"
                    alerts.append({
                        "type": "significant_move",
                        "symbol": symbol,
                        "entry_id": entry.id,
                        "current_price": current_price,
                        "move_percent": entry.current_return_percent,
                        "message": f"{direction} {symbol} moved {entry.current_return_percent:.1f}%! Current: ${current_price:.2f}"
                    })
        
        return alerts
    
    async def _send_websocket_update(self, symbol: str, quote_data: Dict):
        """Send real-time price update via WebSocket"""
        
        try:
            price_update = {
                'type': 'price_update',
                'data': {
                    'symbol': symbol,
                    'price': quote_data.get('price', 0),
                    'change': quote_data.get('change', 0),
                    'change_percent': quote_data.get('change_percent', 0),
                    'volume': quote_data.get('volume', 0),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'realtime_monitor'
                }
            }
            
            # Broadcast to all clients subscribed to this symbol
            await manager.broadcast_to_symbol(symbol, price_update)
            
        except Exception as e:
            logger.error(f"Error sending WebSocket update for {symbol}: {e}")


# Global instance
realtime_price_monitor = RealtimePriceMonitor()
