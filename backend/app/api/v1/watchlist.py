"""
API endpoints for watchlist and performance tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ...core.database import get_db
from ...models.watchlist import WatchlistEntry, WatchlistPriceHistory, PerformanceSummary
from ...services.stock_data import StockDataService
from ...tasks.performance_updater import performance_updater

router = APIRouter()


# Pydantic models for API
class AddToWatchlistRequest(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    entry_type: str  # 'STOCK', 'OPTION_CALL', 'OPTION_PUT'
    entry_price: float
    target_price: float
    stop_loss_price: Optional[float] = None
    ai_confidence_score: float
    ai_recommendation: str
    ai_reasoning: Optional[str] = None
    ai_key_factors: Optional[List[str]] = None
    position_size_dollars: float = 1000.0
    
    # Options-specific fields
    strike_price: Optional[float] = None
    expiration_date: Optional[datetime] = None
    option_contract_symbol: Optional[str] = None


class WatchlistEntryResponse(BaseModel):
    id: int
    symbol: str
    company_name: Optional[str]
    entry_type: str
    entry_price: float
    target_price: float
    stop_loss_price: Optional[float]
    current_price: Optional[float]
    current_return_percent: Optional[float]
    current_return_dollars: Optional[float]
    ai_confidence_score: float
    ai_recommendation: str
    status: str
    is_winner: Optional[bool]
    days_held: int
    entry_date: datetime
    last_price_update: Optional[datetime]
    
    # Options-specific
    strike_price: Optional[float]
    expiration_date: Optional[datetime]


class PerformanceMetrics(BaseModel):
    total_trades: int
    active_trades: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_return: float
    total_return: float
    best_trade_return: float
    worst_trade_return: float
    high_confidence_accuracy: float
    medium_confidence_accuracy: float
    low_confidence_accuracy: float
    stock_win_rate: float
    option_win_rate: float


@router.post("/add", response_model=dict)
async def add_to_watchlist(
    request: AddToWatchlistRequest,
    db: Session = Depends(get_db)
):
    """Add a stock or option to watchlist for performance tracking."""
    try:
        # Calculate position size in shares/contracts
        position_size_shares = request.position_size_dollars / request.entry_price
        
        # Create watchlist entry
        watchlist_entry = WatchlistEntry(
            symbol=request.symbol.upper(),
            company_name=request.company_name,
            entry_type=request.entry_type,
            entry_price=request.entry_price,
            target_price=request.target_price,
            stop_loss_price=request.stop_loss_price,
            ai_confidence_score=request.ai_confidence_score,
            ai_recommendation=request.ai_recommendation,
            ai_reasoning=request.ai_reasoning,
            ai_key_factors=request.ai_key_factors,
            position_size_dollars=request.position_size_dollars,
            position_size_shares=position_size_shares,
            strike_price=request.strike_price,
            expiration_date=request.expiration_date,
            option_contract_symbol=request.option_contract_symbol,
            current_price=request.entry_price,  # Initialize with entry price
            current_return_percent=0.0,
            current_return_dollars=0.0
        )
        
        db.add(watchlist_entry)
        db.commit()
        db.refresh(watchlist_entry)
        
        # Create initial price history entry
        price_history = WatchlistPriceHistory(
            watchlist_entry_id=watchlist_entry.id,
            price=request.entry_price,
            timestamp=datetime.utcnow(),
            return_percent=0.0,
            return_dollars=0.0,
            days_since_entry=0
        )
        
        db.add(price_history)
        db.commit()
        
        return {
            "success": True,
            "message": f"{request.entry_type} {request.symbol} added to watchlist",
            "watchlist_entry_id": watchlist_entry.id,
            "entry_price": request.entry_price,
            "target_price": request.target_price,
            "confidence_score": request.ai_confidence_score
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add to watchlist: {str(e)}")


@router.get("/entries", response_model=List[WatchlistEntryResponse])
async def get_watchlist_entries(
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, CLOSED, EXPIRED"),
    entry_type: Optional[str] = Query(None, description="Filter by type: STOCK, OPTION_CALL, OPTION_PUT"),
    limit: int = Query(50, description="Maximum number of entries to return"),
    db: Session = Depends(get_db)
):
    """Get user's watchlist entries with current performance."""
    try:
        query = db.query(WatchlistEntry)
        
        if status:
            query = query.filter(WatchlistEntry.status == status)
        if entry_type:
            query = query.filter(WatchlistEntry.entry_type == entry_type)
            
        entries = query.order_by(desc(WatchlistEntry.entry_date)).limit(limit).all()
        
        return [
            WatchlistEntryResponse(
                id=entry.id,
                symbol=entry.symbol,
                company_name=entry.company_name,
                entry_type=entry.entry_type,
                entry_price=entry.entry_price,
                target_price=entry.target_price,
                stop_loss_price=entry.stop_loss_price,
                current_price=entry.current_price,
                current_return_percent=entry.current_return_percent,
                current_return_dollars=entry.current_return_dollars,
                ai_confidence_score=entry.ai_confidence_score,
                ai_recommendation=entry.ai_recommendation,
                status=entry.status,
                is_winner=entry.is_winner,
                days_held=entry.days_held,
                entry_date=entry.entry_date,
                last_price_update=entry.last_price_update,
                strike_price=entry.strike_price,
                expiration_date=entry.expiration_date
            )
            for entry in entries
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve watchlist: {str(e)}")


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    days: Optional[int] = Query(None, description="Performance for last N days"),
    db: Session = Depends(get_db)
):
    """Get overall performance metrics for the watchlist."""
    try:
        query = db.query(WatchlistEntry)
        
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(WatchlistEntry.entry_date >= cutoff_date)
        
        all_entries = query.all()
        closed_entries = [e for e in all_entries if e.status in ['CLOSED', 'EXPIRED']]
        
        # Calculate metrics
        total_trades = len(all_entries)
        active_trades = len([e for e in all_entries if e.status == 'ACTIVE'])
        closed_trades = len(closed_entries)
        
        if closed_trades > 0:
            winning_trades = len([e for e in closed_entries if e.is_winner])
            losing_trades = closed_trades - winning_trades
            win_rate = (winning_trades / closed_trades) if closed_trades > 0 else 0.0

            returns = [e.final_return_percent for e in closed_entries if e.final_return_percent is not None]
            average_return = sum(returns) / len(returns) if returns else 0.0
            total_return = sum(returns) if returns else 0.0
            best_trade_return = max(returns) if returns else 0.0
            worst_trade_return = min(returns) if returns else 0.0
        else:
            winning_trades = 0
            losing_trades = 0
            win_rate = 0.0
            average_return = 0.0
            total_return = 0.0
            best_trade_return = 0.0
            worst_trade_return = 0.0
        
        # AI accuracy by confidence level
        high_conf_entries = [e for e in closed_entries if e.ai_confidence_score >= 80]
        high_conf_winners = len([e for e in high_conf_entries if e.is_winner])
        high_confidence_accuracy = (high_conf_winners / len(high_conf_entries) * 100) if high_conf_entries else 0.0
        
        med_conf_entries = [e for e in closed_entries if 60 <= e.ai_confidence_score < 80]
        med_conf_winners = len([e for e in med_conf_entries if e.is_winner])
        medium_confidence_accuracy = (med_conf_winners / len(med_conf_entries) * 100) if med_conf_entries else 0.0
        
        low_conf_entries = [e for e in closed_entries if e.ai_confidence_score < 60]
        low_conf_winners = len([e for e in low_conf_entries if e.is_winner])
        low_confidence_accuracy = (low_conf_winners / len(low_conf_entries)) if low_conf_entries else 0.0

        # Asset type performance
        stock_entries = [e for e in closed_entries if e.entry_type == 'STOCK']
        stock_winners = len([e for e in stock_entries if e.is_winner])
        stock_win_rate = (stock_winners / len(stock_entries)) if stock_entries else 0.0

        option_entries = [e for e in closed_entries if e.entry_type.startswith('OPTION_')]
        option_winners = len([e for e in option_entries if e.is_winner])
        option_win_rate = (option_winners / len(option_entries)) if option_entries else 0.0

        return PerformanceMetrics(
            total_trades=total_trades,
            active_trades=active_trades,
            closed_trades=closed_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            average_return=average_return,
            total_return=total_return,
            best_trade_return=best_trade_return,
            worst_trade_return=worst_trade_return,
            high_confidence_accuracy=high_confidence_accuracy,
            medium_confidence_accuracy=medium_confidence_accuracy,
            low_confidence_accuracy=low_confidence_accuracy,
            stock_win_rate=stock_win_rate,
            option_win_rate=option_win_rate
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.post("/update-performance", response_model=dict)
async def update_performance(db: Session = Depends(get_db)):
    """Manually trigger performance update for all active watchlist entries."""
    try:
        result = await performance_updater.update_all_active_entries(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance update failed: {str(e)}")


@router.post("/cleanup-history", response_model=dict)
async def cleanup_price_history(
    days_to_keep: int = Query(90, description="Number of days of price history to keep"),
    db: Session = Depends(get_db)
):
    """Clean up old price history entries."""
    try:
        deleted_count = await performance_updater.cleanup_old_price_history(db, days_to_keep)
        return {
            "status": "success",
            "message": f"Cleaned up {deleted_count} old price history entries",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate performance metrics: {str(e)}")


@router.post("/update-prices")
async def update_watchlist_prices(db: Session = Depends(get_db)):
    """Update current prices for all active watchlist entries."""
    try:
        active_entries = db.query(WatchlistEntry).filter(WatchlistEntry.status == 'ACTIVE').all()
        
        updated_count = 0
        async with StockDataService() as stock_service:
            for entry in active_entries:
                try:
                    # Get current price
                    if entry.entry_type == 'STOCK':
                        quote_data = await stock_service.get_real_time_quote(entry.symbol)
                        if quote_data:
                            current_price = quote_data.get('price', 0)
                        else:
                            continue
                    else:
                        # For options, we'd need options pricing API (future enhancement)
                        # For now, skip options price updates
                        continue
                    
                    # Calculate performance
                    return_percent = ((current_price - entry.entry_price) / entry.entry_price) * 100
                    return_dollars = (current_price - entry.entry_price) * entry.position_size_shares
                    days_held = (datetime.utcnow() - entry.entry_date).days
                    
                    # Update entry
                    entry.current_price = current_price
                    entry.current_return_percent = return_percent
                    entry.current_return_dollars = return_dollars
                    entry.days_held = days_held
                    entry.last_price_update = datetime.utcnow()
                    entry.price_update_count += 1
                    
                    # Check if target or stop loss hit
                    if entry.target_price and current_price >= entry.target_price:
                        entry.status = 'CLOSED'
                        entry.is_winner = True
                        entry.exit_price = current_price
                        entry.exit_date = datetime.utcnow()
                        entry.exit_reason = 'TARGET_HIT'
                        entry.final_return_percent = return_percent
                        entry.final_return_dollars = return_dollars
                    elif entry.stop_loss_price and current_price <= entry.stop_loss_price:
                        entry.status = 'CLOSED'
                        entry.is_winner = False
                        entry.exit_price = current_price
                        entry.exit_date = datetime.utcnow()
                        entry.exit_reason = 'STOP_LOSS'
                        entry.final_return_percent = return_percent
                        entry.final_return_dollars = return_dollars
                    
                    # Add price history entry
                    price_history = WatchlistPriceHistory(
                        watchlist_entry_id=entry.id,
                        price=current_price,
                        timestamp=datetime.utcnow(),
                        return_percent=return_percent,
                        return_dollars=return_dollars,
                        days_since_entry=days_held
                    )
                    db.add(price_history)
                    
                    updated_count += 1
                    
                except Exception as e:
                    print(f"Error updating {entry.symbol}: {e}")
                    continue
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Updated prices for {updated_count} watchlist entries",
            "updated_count": updated_count,
            "total_active": len(active_entries)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update prices: {str(e)}")


@router.delete("/entry/{entry_id}")
async def remove_from_watchlist(
    entry_id: int,
    db: Session = Depends(get_db)
):
    """Remove an entry from the watchlist."""
    try:
        entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Watchlist entry not found")
        
        db.delete(entry)
        db.commit()
        
        return {
            "success": True,
            "message": f"Removed {entry.symbol} from watchlist"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to remove from watchlist: {str(e)}")
