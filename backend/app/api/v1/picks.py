# backend/app/api/v1/picks.py
"""
Picks API - Serves live AI picks to frontend
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/picks", tags=["picks"])
logger = logging.getLogger(__name__)


@router.get("/live")
async def get_live_picks(
    sentiment: Optional[str] = Query(None, description="Filter by bullish or bearish"),
    limit: int = Query(25, ge=1, le=100),
    min_confidence: int = Query(48, ge=0, le=100)
):
    """
    Get live AI picks from database with real-time prices from FMP.
    Returns picks from the last 48 hours that meet confidence threshold.
    """
    try:
        from app.core.database import get_asyncpg_pool
        from app.core.config import settings
        import httpx

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Check if picks table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'picks'
                )
            """)

            if not exists:
                logger.warning("Picks table doesn't exist yet")
                return []

            # Build query based on filters
            query = """
                SELECT
                    id, symbol, direction, confidence, reasoning,
                    target_low, target_high, pick_context,
                    created_at, expires_at
                FROM picks
                WHERE confidence >= $1
                AND created_at >= $2
            """
            params = [min_confidence / 100.0, datetime.utcnow() - timedelta(hours=48)]

            if sentiment:
                query += " AND direction = $3"
                params.append(sentiment)

            query += " ORDER BY confidence DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query, *params)

            # Get chart URLs from shortlist_candidates
            symbol_list = [row["symbol"] for row in rows]
            chart_data = {}
            price_at_pick = {}

            if symbol_list:
                # Get latest shortlist date
                date_row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
                if date_row and date_row['latest_date']:
                    shortlist_date = date_row['latest_date']

                    # Get chart URLs and prices for these symbols
                    chart_rows = await conn.fetch("""
                        SELECT symbol, chart_url, price_at_selection
                        FROM shortlist_candidates
                        WHERE date = $1 AND symbol = ANY($2)
                    """, shortlist_date, symbol_list)

                    for cr in chart_rows:
                        chart_data[cr["symbol"]] = cr["chart_url"]
                        price_at_pick[cr["symbol"]] = float(cr["price_at_selection"]) if cr["price_at_selection"] else None

            # Fetch real-time prices from FMP (batch quote)
            current_prices = {}
            if symbol_list and settings.FMP_API_KEY:
                try:
                    symbols_str = ",".join(symbol_list)
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(
                            f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}",
                            params={"apikey": settings.FMP_API_KEY}
                        )
                        if resp.status_code == 200:
                            quotes = resp.json()
                            for q in quotes:
                                current_prices[q["symbol"]] = float(q.get("price", 0))
                except Exception as e:
                    logger.warning(f"Failed to fetch FMP quotes: {e}")

            # Transform to frontend format
            picks = []
            for row in rows:
                symbol = row["symbol"]
                # confidence is already stored as a decimal (0.85) or percentage (85) - check value
                conf_value = float(row["confidence"]) if row["confidence"] else 0
                # If confidence > 1, it's already a percentage; otherwise multiply by 100
                confidence_pct = conf_value if conf_value > 1 else conf_value * 100

                entry_price = price_at_pick.get(symbol)
                current_price = current_prices.get(symbol) or entry_price

                # Calculate % change since picked
                change_pct = None
                if entry_price and current_price and entry_price > 0:
                    change_pct = ((current_price - entry_price) / entry_price) * 100

                picks.append({
                    "id": row["id"],
                    "symbol": symbol,
                    "direction": row["direction"],
                    "confidence": confidence_pct,
                    "reasoning": row["reasoning"],
                    "target_low": float(row["target_low"]) if row["target_low"] else None,
                    "target_high": float(row["target_high"]) if row["target_high"] else None,
                    "context": row["pick_context"],
                    "chart_url": chart_data.get(symbol),
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "change_pct": round(change_pct, 2) if change_pct is not None else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                })

            return picks

    except Exception as e:
        logger.error(f"Error fetching picks: {e}")
        # Return empty list instead of error for graceful frontend handling
        return []


@router.get("/today")
async def get_todays_picks():
    """Get today's picks summary for dashboard badge"""
    try:
        from app.core.database import get_asyncpg_pool
        
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Check if picks table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'picks'
                )
            """)
            
            if not exists:
                return {"bullish": 0, "bearish": 0, "total": 0, "last_updated": None}
            
            today = datetime.utcnow().date()
            
            result = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE direction = 'bullish') as bullish,
                    COUNT(*) FILTER (WHERE direction = 'bearish') as bearish,
                    COUNT(*) as total,
                    MAX(created_at) as last_updated
                FROM picks
                WHERE DATE(created_at) = $1
            """, today)
            
            return {
                "bullish": result["bullish"] or 0,
                "bearish": result["bearish"] or 0,
                "total": result["total"] or 0,
                "last_updated": result["last_updated"].isoformat() if result["last_updated"] else None
            }
            
    except Exception as e:
        logger.error(f"Error fetching today's picks: {e}")
        return {"bullish": 0, "bearish": 0, "total": 0, "last_updated": None}

