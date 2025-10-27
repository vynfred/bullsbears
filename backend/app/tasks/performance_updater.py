"""
Background task for updating watchlist performance with current market prices.
This module handles automatic price updates and performance calculations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..core.database import get_db
from ..models.watchlist import WatchlistEntry, WatchlistPriceHistory
from ..services.stock_data import StockDataService
from ..core.config import settings

logger = logging.getLogger(__name__)


class PerformanceUpdater:
    """Handles automatic performance updates for watchlist entries."""
    
    def __init__(self):
        self.stock_service = StockDataService()
    
    async def update_all_active_entries(self, db: Session) -> dict:
        """Update prices and performance for all active watchlist entries."""
        try:
            # Get all active entries
            active_entries = db.query(WatchlistEntry).filter(
                WatchlistEntry.status == 'ACTIVE'
            ).all()
            
            if not active_entries:
                logger.info("No active watchlist entries to update")
                return {
                    "status": "success",
                    "message": "No active entries to update",
                    "updated_count": 0,
                    "failed_count": 0
                }
            
            logger.info(f"Updating {len(active_entries)} active watchlist entries")
            
            updated_count = 0
            failed_count = 0
            
            for entry in active_entries:
                try:
                    success = await self._update_entry_performance(db, entry)
                    if success:
                        updated_count += 1
                    else:
                        failed_count += 1
                        
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Failed to update entry {entry.id} ({entry.symbol}): {str(e)}")
                    failed_count += 1
            
            # Commit all updates
            db.commit()
            
            logger.info(f"Performance update completed: {updated_count} updated, {failed_count} failed")
            
            return {
                "status": "success",
                "message": f"Updated {updated_count} entries, {failed_count} failed",
                "updated_count": updated_count,
                "failed_count": failed_count,
                "total_entries": len(active_entries)
            }
            
        except Exception as e:
            logger.error(f"Error in update_all_active_entries: {str(e)}")
            db.rollback()
            return {
                "status": "error",
                "message": f"Update failed: {str(e)}",
                "updated_count": 0,
                "failed_count": 0
            }
    
    async def _update_entry_performance(self, db: Session, entry: WatchlistEntry) -> bool:
        """Update performance for a single watchlist entry."""
        try:
            # Get current price based on entry type
            if entry.entry_type == 'STOCK':
                current_price = await self._get_stock_price(entry.symbol)
            elif entry.entry_type.startswith('OPTION_'):
                # For options, we'll use the underlying stock price for now
                # In a real implementation, you'd get option prices from a provider
                current_price = await self._get_stock_price(entry.symbol)
                if current_price:
                    # Apply a simple option pricing approximation
                    current_price = self._estimate_option_price(entry, current_price)
            else:
                logger.warning(f"Unknown entry type: {entry.entry_type}")
                return False
            
            if current_price is None:
                logger.warning(f"Could not get price for {entry.symbol}")
                return False
            
            # Calculate performance metrics
            entry_price = entry.entry_price
            return_percent = ((current_price - entry_price) / entry_price) * 100
            return_dollars = (current_price - entry_price) * (entry.position_size_shares or 1)
            
            # Calculate days held
            days_held = (datetime.utcnow() - entry.entry_date).days
            
            # Update entry
            entry.current_price = current_price
            entry.current_return_percent = return_percent
            entry.current_return_dollars = return_dollars
            entry.days_held = days_held
            entry.last_price_update = datetime.utcnow()
            entry.price_update_count = (entry.price_update_count or 0) + 1
            entry.updated_at = datetime.utcnow()
            
            # Check if target or stop loss hit
            if entry.target_price and current_price >= entry.target_price:
                entry.status = 'CLOSED'
                entry.is_winner = True
                entry.exit_price = current_price
                entry.exit_date = datetime.utcnow()
                entry.exit_reason = 'TARGET_HIT'
                entry.final_return_percent = return_percent
                entry.final_return_dollars = return_dollars
                logger.info(f"Target hit for {entry.symbol}: ${current_price} >= ${entry.target_price}")
            
            elif entry.stop_loss_price and current_price <= entry.stop_loss_price:
                entry.status = 'CLOSED'
                entry.is_winner = False
                entry.exit_price = current_price
                entry.exit_date = datetime.utcnow()
                entry.exit_reason = 'STOP_LOSS_HIT'
                entry.final_return_percent = return_percent
                entry.final_return_dollars = return_dollars
                logger.info(f"Stop loss hit for {entry.symbol}: ${current_price} <= ${entry.stop_loss_price}")
            
            # Add price history entry
            price_history = WatchlistPriceHistory(
                watchlist_entry_id=entry.id,
                price=current_price,
                timestamp=datetime.utcnow(),
                return_percent=return_percent,
                return_dollars=return_dollars,
                days_since_entry=days_held,
                data_source='alpha_vantage',
                is_real_time=True
            )
            db.add(price_history)
            
            logger.debug(f"Updated {entry.symbol}: ${current_price} ({return_percent:+.1f}%)")
            return True
            
        except Exception as e:
            logger.error(f"Error updating entry {entry.id}: {str(e)}")
            return False
    
    async def _get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price."""
        try:
            quote_data = await self.stock_service.get_real_time_quote(symbol)
            if quote_data and 'price' in quote_data:
                return float(quote_data['price'])
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None
    
    def _estimate_option_price(self, entry: WatchlistEntry, underlying_price: float) -> float:
        """
        Simple option price estimation based on intrinsic value.
        In a real implementation, you'd use Black-Scholes or get real option prices.
        """
        if not entry.strike_price:
            return underlying_price
        
        if entry.entry_type == 'OPTION_CALL':
            # Call option intrinsic value
            intrinsic_value = max(0, underlying_price - entry.strike_price)
        else:  # OPTION_PUT
            # Put option intrinsic value
            intrinsic_value = max(0, entry.strike_price - underlying_price)
        
        # Add some time value (very simplified)
        if entry.expiration_date:
            days_to_expiry = (entry.expiration_date - datetime.utcnow()).days
            time_value = max(0, days_to_expiry * 0.01)  # $0.01 per day
        else:
            time_value = 0.5  # Default time value
        
        return max(0.01, intrinsic_value + time_value)  # Minimum $0.01
    
    async def cleanup_old_price_history(self, db: Session, days_to_keep: int = 90) -> int:
        """Clean up old price history entries to keep database size manageable."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted_count = db.query(WatchlistPriceHistory).filter(
                WatchlistPriceHistory.timestamp < cutoff_date
            ).delete()
            
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old price history entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up price history: {str(e)}")
            db.rollback()
            return 0


# Global instance
performance_updater = PerformanceUpdater()


async def run_daily_performance_update():
    """Run the daily performance update task."""
    logger.info("Starting daily performance update")
    
    db = next(get_db())
    try:
        result = await performance_updater.update_all_active_entries(db)
        logger.info(f"Daily performance update completed: {result}")
        
        # Also cleanup old price history
        cleanup_count = await performance_updater.cleanup_old_price_history(db)
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} old price history entries")
        
        return result
        
    finally:
        db.close()


async def run_hourly_performance_update():
    """Run hourly performance updates during market hours."""
    logger.info("Starting hourly performance update")
    
    # Check if it's market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
    now = datetime.utcnow()
    # Convert to ET (approximate, doesn't handle DST perfectly)
    et_hour = (now.hour - 5) % 24
    is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
    is_market_hours = is_weekday and 9 <= et_hour <= 16
    
    if not is_market_hours:
        logger.info("Outside market hours, skipping hourly update")
        return {"status": "skipped", "reason": "outside_market_hours"}
    
    db = next(get_db())
    try:
        result = await performance_updater.update_all_active_entries(db)
        logger.info(f"Hourly performance update completed: {result}")
        return result
        
    finally:
        db.close()
