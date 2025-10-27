"""
API endpoints for earnings calendar and earnings-driven analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ...core.database import get_db
from ...core.redis_client import redis_client
from ...models.precomputed_analysis import PrecomputedAnalysis
from ...services.catalyst_detector import CatalystDetector
from ...tasks.precompute import trigger_update_single_stock
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/earnings", tags=["earnings"])


class EarningsEvent(BaseModel):
    symbol: str
    company_name: str
    earnings_date: str
    estimated_eps: Optional[float] = None
    actual_eps: Optional[float] = None
    surprise_percent: Optional[float] = None
    market_cap: Optional[float] = None
    last_quarter_eps: Optional[float] = None
    last_quarter_surprise: Optional[float] = None
    ai_sentiment: Optional[str] = None
    ai_summary: Optional[str] = None
    sector: str
    time: str  # BMO, AMC, TBD
    has_analysis: bool = False
    analysis_age_minutes: Optional[int] = None


class EarningsCalendarResponse(BaseModel):
    events: List[EarningsEvent]
    total_events: int
    date_range: Dict[str, str]
    last_updated: str


@router.get("/calendar", response_model=EarningsCalendarResponse)
async def get_earnings_calendar(
    days_ahead: int = Query(7, description="Number of days ahead to fetch earnings"),
    include_analysis_status: bool = Query(True, description="Include analysis availability status"),
    db: Session = Depends(get_db)
) -> EarningsCalendarResponse:
    """
    Get upcoming earnings calendar with AI sentiment and analysis status.
    
    This endpoint provides:
    - Upcoming earnings events for the next N days
    - Basic AI sentiment for each stock (cached)
    - Analysis availability status (whether stock has been analyzed)
    - Market timing (BMO/AMC/TBD)
    """
    try:
        # Get earnings events from catalyst detector
        async with CatalystDetector() as detector:
            catalysts = await detector.detect_catalysts("", days_ahead=days_ahead)
        
        # Filter for earnings events only
        earnings_catalysts = [c for c in catalysts if c.event_type == 'EARNINGS']
        
        events = []
        for catalyst in earnings_catalysts:
            # Get basic company info (mock for now - would integrate with real data)
            event = EarningsEvent(
                symbol=catalyst.symbol,
                company_name=catalyst.details.get('company_name', f"{catalyst.symbol} Inc."),
                earnings_date=catalyst.date.isoformat(),
                estimated_eps=catalyst.details.get('eps_estimate'),
                sector=catalyst.details.get('sector', 'Technology'),
                time=catalyst.details.get('timing', 'TBD'),
                ai_sentiment=await _get_cached_sentiment(catalyst.symbol),
                ai_summary=await _get_cached_summary(catalyst.symbol),
                last_quarter_eps=catalyst.details.get('last_quarter_eps'),
                last_quarter_surprise=catalyst.details.get('last_quarter_surprise')
            )
            
            # Check if analysis exists if requested
            if include_analysis_status:
                analysis_info = await _check_analysis_status(catalyst.symbol, db)
                event.has_analysis = analysis_info['has_analysis']
                event.analysis_age_minutes = analysis_info['age_minutes']
            
            events.append(event)
        
        # Sort by date and impact
        events.sort(key=lambda x: (x.earnings_date, x.symbol))
        
        return EarningsCalendarResponse(
            events=events,
            total_events=len(events),
            date_range={
                "start": datetime.now().isoformat(),
                "end": (datetime.now() + timedelta(days=days_ahead)).isoformat()
            },
            last_updated=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error fetching earnings calendar: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch earnings calendar: {str(e)}")


@router.post("/precompute-popular")
async def precompute_popular_earnings(
    background_tasks: BackgroundTasks,
    days_ahead: int = Query(3, description="Days ahead to precompute"),
    min_market_cap: float = Query(1000000000, description="Minimum market cap for precompute"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger precompute analysis for popular upcoming earnings stocks.
    
    This helps ensure popular earnings stocks are analyzed before users request them,
    reducing API load and improving user experience.
    """
    try:
        # Get upcoming earnings
        async with CatalystDetector() as detector:
            catalysts = await detector.detect_catalysts("", days_ahead=days_ahead)
        
        earnings_catalysts = [c for c in catalysts if c.event_type == 'EARNINGS']
        
        # Filter by market cap and popularity (mock logic for now)
        popular_symbols = []
        for catalyst in earnings_catalysts:
            market_cap = catalyst.details.get('market_cap', 0)
            if market_cap >= min_market_cap:
                popular_symbols.append(catalyst.symbol)
        
        # Trigger background analysis for each symbol
        triggered_count = 0
        for symbol in popular_symbols[:10]:  # Limit to top 10 to avoid API overload
            try:
                # Check if analysis is recent enough
                analysis_info = await _check_analysis_status(symbol, db)
                if not analysis_info['has_analysis'] or analysis_info['age_minutes'] > 60:
                    background_tasks.add_task(trigger_update_single_stock, symbol)
                    triggered_count += 1
            except Exception as e:
                logger.warning(f"Failed to trigger precompute for {symbol}: {e}")
        
        return {
            "success": True,
            "message": f"Triggered precompute for {triggered_count} popular earnings stocks",
            "symbols_triggered": popular_symbols[:triggered_count],
            "total_earnings_found": len(earnings_catalysts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in precompute popular earnings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger precompute: {str(e)}")


async def _get_cached_sentiment(symbol: str) -> Optional[str]:
    """Get cached AI sentiment for a symbol."""
    try:
        cache_key = f"earnings_sentiment:{symbol}"
        cached = await redis_client.get(cache_key)
        if cached:
            return cached
        
        # Generate basic sentiment (would integrate with AI service)
        # For now, return mock sentiment
        import random
        sentiments = ["Bullish", "Bearish", "Neutral"]
        sentiment = random.choice(sentiments)
        
        # Cache for 1 hour
        await redis_client.setex(cache_key, 3600, sentiment)
        return sentiment
        
    except Exception:
        return None


async def _get_cached_summary(symbol: str) -> Optional[str]:
    """Get cached AI summary for a symbol."""
    try:
        cache_key = f"earnings_summary:{symbol}"
        cached = await redis_client.get(cache_key)
        if cached:
            return cached
        
        # Generate basic summary (would integrate with AI service)
        summary = f"Upcoming earnings for {symbol}. Market expectations and analyst sentiment to be analyzed."
        
        # Cache for 1 hour
        await redis_client.setex(cache_key, 3600, summary)
        return summary
        
    except Exception:
        return None


async def _check_analysis_status(symbol: str, db: Session) -> Dict[str, Any]:
    """Check if analysis exists and how old it is."""
    try:
        # Check precomputed analysis
        analysis = db.query(PrecomputedAnalysis).filter(
            PrecomputedAnalysis.symbol == symbol.upper()
        ).order_by(desc(PrecomputedAnalysis.updated_at)).first()
        
        if analysis:
            age_minutes = int((datetime.utcnow() - analysis.updated_at).total_seconds() / 60)
            return {
                "has_analysis": True,
                "age_minutes": age_minutes,
                "is_fresh": age_minutes < 60  # Consider fresh if less than 1 hour old
            }
        
        return {
            "has_analysis": False,
            "age_minutes": None,
            "is_fresh": False
        }
        
    except Exception as e:
        logger.warning(f"Error checking analysis status for {symbol}: {e}")
        return {
            "has_analysis": False,
            "age_minutes": None,
            "is_fresh": False
        }


@router.post("/trigger-analysis/{symbol}")
async def trigger_earnings_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force analysis even if recent analysis exists"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger analysis for a specific earnings stock.
    
    This endpoint is called when a user clicks on an earnings stock
    that hasn't been analyzed yet or needs fresh analysis.
    """
    try:
        symbol = symbol.upper().strip()
        
        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol format")
        
        # Check existing analysis unless forced
        if not force:
            analysis_info = await _check_analysis_status(symbol, db)
            if analysis_info['has_analysis'] and analysis_info['is_fresh']:
                return {
                    "success": True,
                    "message": f"Recent analysis already exists for {symbol}",
                    "analysis_age_minutes": analysis_info['age_minutes'],
                    "triggered_new_analysis": False,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Trigger background analysis
        task = trigger_update_single_stock(symbol)
        
        return {
            "success": True,
            "message": f"Analysis triggered for {symbol}",
            "task_id": task.id if hasattr(task, 'id') else None,
            "symbol": symbol,
            "triggered_new_analysis": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger analysis: {str(e)}")
