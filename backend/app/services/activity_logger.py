# backend/app/services/activity_logger.py
"""
Pipeline Activity Logger - logs all pipeline steps for admin visibility
"""
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def log_activity(
    step: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    tier_counts: Optional[Dict[str, int]] = None,
    duration_seconds: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """
    Log pipeline activity to database for admin dashboard visibility.
    
    Args:
        step: Pipeline step name (fmp_update, prescreen, charts, vision, social, arbitrator, learner)
        action: What happened (started, completed, error, etc.)
        details: Additional details as dict (will be stored as JSONB)
        tier_counts: Stock counts by tier {"all": X, "active": Y, "shortlist": Z, "picks": W}
        duration_seconds: How long the step took
        success: Whether the step succeeded
        error_message: Error message if failed
    """
    try:
        from app.core.database import get_asyncpg_pool
        
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Ensure table exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_activity (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    step VARCHAR(50) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    details JSONB,
                    tier_counts JSONB,
                    duration_seconds DECIMAL(10, 2),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)
            
            await conn.execute("""
                INSERT INTO pipeline_activity (step, action, details, tier_counts, duration_seconds, success, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                step,
                action,
                json.dumps(details) if details else None,
                json.dumps(tier_counts) if tier_counts else None,
                duration_seconds,
                success,
                error_message
            )
            
            # Keep only last 500 entries to avoid bloat
            await conn.execute("""
                DELETE FROM pipeline_activity 
                WHERE id NOT IN (
                    SELECT id FROM pipeline_activity ORDER BY timestamp DESC LIMIT 500
                )
            """)
            
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")


async def get_recent_activity(limit: int = 50) -> list:
    """Get recent pipeline activity for admin dashboard"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Ensure table exists before querying
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_activity (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    step VARCHAR(50) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    details JSONB,
                    tier_counts JSONB,
                    duration_seconds DECIMAL(10, 2),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)

            rows = await conn.fetch("""
                SELECT
                    timestamp, step, action, details, tier_counts,
                    duration_seconds, success, error_message
                FROM pipeline_activity
                ORDER BY timestamp DESC
                LIMIT $1
            """, limit)

            return [
                {
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    "step": row["step"],
                    "action": row["action"],
                    "details": json.loads(row["details"]) if row["details"] else None,
                    "tier_counts": json.loads(row["tier_counts"]) if row["tier_counts"] else None,
                    "duration_seconds": float(row["duration_seconds"]) if row["duration_seconds"] else None,
                    "success": row["success"],
                    "error_message": row["error_message"]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get activity: {e}")
        return []


async def get_tier_counts() -> Dict[str, int]:
    """Get current stock counts by tier"""
    try:
        from app.core.database import get_asyncpg_pool
        
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # ALL tier - total unique symbols in OHLC
            all_count = await conn.fetchval(
                "SELECT COUNT(DISTINCT symbol) FROM prime_ohlc_90d"
            ) or 0
            
            # ACTIVE tier - from classifications
            active_count = await conn.fetchval(
                "SELECT COUNT(*) FROM stock_classifications WHERE current_tier = 'ACTIVE'"
            ) or 0
            
            # SHORT_LIST - today's shortlist
            shortlist_count = await conn.fetchval(
                "SELECT COUNT(*) FROM shortlist_candidates WHERE date = CURRENT_DATE"
            ) or 0
            
            # PICKS - today's picks
            picks_count = await conn.fetchval(
                "SELECT COUNT(*) FROM picks WHERE DATE(created_at) = CURRENT_DATE"
            ) or 0
            
            return {
                "all": all_count,
                "active": active_count,
                "shortlist": shortlist_count,
                "picks": picks_count
            }
    except Exception as e:
        logger.error(f"Failed to get tier counts: {e}")
        return {"all": 0, "active": 0, "shortlist": 0, "picks": 0}

