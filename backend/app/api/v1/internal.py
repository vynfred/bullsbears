# app/api/v1/internal.py
from fastapi import APIRouter, HTTPException
from app.services.system_state import is_system_on, set_system_on

router = APIRouter()


@router.get("/health")
async def internal_health():
    return {
        "status": "healthy",
        "app": "BullsBears v5 – Render Edition",
        "environment": "production",
        "database": "Render Postgres (internal)",
        "queue": "Render Redis (internal)",
        "llm": "Fireworks qwen2.5-72b-instruct",
        "vision": "Groq Llama-3.2-11B-Vision",
        "social": "Grok-4",
        "system_state": "ON" if await is_system_on() else "OFF",
    }


@router.post("/system/on")
async def turn_system_on():
    await set_system_on(True)
    return {"status": "System turned ON – daily pipeline will run at 8:00 AM ET"}


@router.post("/system/off")
async def turn_system_off():
    await set_system_on(False)
    return {"status": "System turned OFF – no pipeline until turned back on"}


@router.get("/system/status")
async def get_system_status():
    return {"system_on": await is_system_on()}


@router.get("/data/freshness")
async def get_data_freshness_public():
    """Public endpoint to check FMP data freshness (no auth required)."""
    from app.core.database import get_asyncpg_pool
    from datetime import datetime
    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # OHLC data freshness
            ohlc = await conn.fetchrow("""
                SELECT
                    MAX(date) as latest_date,
                    MIN(date) as oldest_date,
                    COUNT(*) as total_rows
                FROM ohlc_daily
            """)

            # Active symbols count
            active = await conn.fetchval("""
                SELECT COUNT(*) FROM stock_universe WHERE classification = 'ACTIVE'
            """)

            # Shortlist today
            shortlist_today = await conn.fetchval("""
                SELECT COUNT(*) FROM shortlist_candidates WHERE date = CURRENT_DATE
            """)

            # Picks today
            picks_today = await conn.fetchval("""
                SELECT COUNT(*) FROM picks WHERE DATE(created_at) = CURRENT_DATE
            """)

            return {
                "ohlc_latest": str(ohlc["latest_date"]) if ohlc["latest_date"] else None,
                "ohlc_rows": ohlc["total_rows"] or 0,
                "active_symbols": active or 0,
                "shortlist_today": shortlist_today or 0,
                "picks_today": picks_today or 0,
                "server_time": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {"error": str(e)}