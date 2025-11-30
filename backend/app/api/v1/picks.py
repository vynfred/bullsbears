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
    Get live AI picks from database.
    Returns picks from the last 24 hours that meet confidence threshold.
    """
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
            
            # Transform to frontend format
            picks = []
            for row in rows:
                picks.append({
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "direction": row["direction"],
                    "confidence": float(row["confidence"]) * 100,  # Convert to percentage
                    "reasoning": row["reasoning"],
                    "target_low": float(row["target_low"]) if row["target_low"] else None,
                    "target_high": float(row["target_high"]) if row["target_high"] else None,
                    "context": row["pick_context"],
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

