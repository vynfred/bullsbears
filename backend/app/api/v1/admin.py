# backend/app/api/v1/admin.py
"""
BullsBears Admin API - JWT protected, clean v2.
Only accessible via /admin/* (behind secret prefix + auth)

ENDPOINTS:
- Auth: /auth/login
- System: /system/status, /system/on, /system/off
- Health: /health
- Database: /init-db, /reset-pipeline-tables
- Data: /prime-data, /build-active, /prime-status
- Dashboard: /data/stats, /data/freshness, /data/activity, /data/picks, /data/shortlist, /data/stocks
- Pipeline: /trigger-full-pipeline, /trigger-prescreen, /trigger-charts, /trigger-vision, /trigger-social, /trigger-arbitrator
- Utilities: /clear-picks, /dedupe-picks, /trigger-outcome-monitor, /trigger-pretty-charts
"""

import logging
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_asyncpg_pool
from app.core.security import create_access_token, verify_admin_token, verify_admin_credentials
from app.services.system_state import is_system_on, set_system_on, _get_redis_client

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# ========================= MODELS =========================
class LoginResponse(BaseModel):
    success: bool
    access_token: str | None = None
    token_type: str = "bearer"
    message: str = ""


# ========================= AUTH =========================
@router.post("/auth/login", response_model=LoginResponse)
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Admin login - returns JWT token valid for 30 days."""
    if verify_admin_credentials(form_data.username, form_data.password):
        token = create_access_token({"sub": "admin"}, expires_delta=timedelta(days=30))
        return LoginResponse(success=True, access_token=token, message="Login successful")
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ========================= SYSTEM CONTROL =========================
@router.get("/system/status", dependencies=[Depends(verify_admin_token)])
async def get_system_status():
    """Get current system on/off state."""
    try:
        system_on = await is_system_on()
        return {"system_on": system_on, "status": "ON" if system_on else "OFF"}
    except Exception as e:
        return {"system_on": False, "status": "ERROR", "error": str(e)}


@router.post("/system/on", dependencies=[Depends(verify_admin_token)])
async def turn_system_on():
    """Turn system ON."""
    success = await set_system_on(True)
    return {"success": success, "message": "System turned ON" if success else "Failed"}


@router.post("/system/off", dependencies=[Depends(verify_admin_token)])
async def turn_system_off():
    """Turn system OFF."""
    success = await set_system_on(False)
    return {"success": success, "message": "System turned OFF" if success else "Failed"}


# ========================= HEALTH =========================
@router.get("/health", dependencies=[Depends(verify_admin_token)])
async def admin_health_check():
    """Check health of all services with actual connectivity tests."""
    import httpx
    health = {"render": True, "database": False, "redis": False, "fireworks": False}

    # Ping database (fix #6 - actually test connection)
    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            await conn.fetchval("SELECT 1")
            health["database"] = True
    except Exception:
        pass

    # Ping Redis
    try:
        client = _get_redis_client()
        if client:
            await client.ping()
            health["redis"] = True
    except Exception:
        pass

    # Check Fireworks API (strip key from response - fix #8)
    if settings.FIREWORKS_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.fireworks.ai/inference/v1/models",
                    headers={"Authorization": f"Bearer {settings.FIREWORKS_API_KEY}"}
                )
                health["fireworks"] = resp.status_code == 200
        except Exception:
            pass

    return health


# ========================= DATABASE =========================
@router.post("/init-db", dependencies=[Depends(verify_admin_token)])
async def init_database():
    """Initialize all database tables (idempotent). Uses db_migration.py."""
    from app.services.db_migration import run_all_migrations
    return await run_all_migrations()


@router.post("/reset-pipeline-tables", dependencies=[Depends(verify_admin_token)])
async def reset_pipeline_tables():
    """DROP and recreate pipeline tables. WARNING: Deletes all picks data!"""
    from app.services.db_migration import reset_all_pipeline_tables
    return await reset_all_pipeline_tables()


# ========================= DATA ENDPOINTS =========================
@router.get("/data/freshness", dependencies=[Depends(verify_admin_token)])
async def get_data_freshness():
    """Check freshness of FMP data, shortlist, and picks."""
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

            # Shortlist freshness
            shortlist = await conn.fetchrow("""
                SELECT
                    MAX(date) as latest_date,
                    COUNT(*) FILTER (WHERE date = CURRENT_DATE) as today_count
                FROM shortlist_candidates
            """)

            # Picks freshness
            picks = await conn.fetchrow("""
                SELECT
                    MAX(created_at) as latest_created,
                    COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as today_count
                FROM picks
            """)

            # Active symbols count
            active = await conn.fetchval("""
                SELECT COUNT(*) FROM stock_universe WHERE classification = 'ACTIVE'
            """)

            return {
                "ohlc": {
                    "latest_date": str(ohlc["latest_date"]) if ohlc["latest_date"] else None,
                    "oldest_date": str(ohlc["oldest_date"]) if ohlc["oldest_date"] else None,
                    "total_rows": ohlc["total_rows"] or 0
                },
                "shortlist": {
                    "latest_date": str(shortlist["latest_date"]) if shortlist["latest_date"] else None,
                    "today_count": shortlist["today_count"] or 0
                },
                "picks": {
                    "latest_created": str(picks["latest_created"]) if picks["latest_created"] else None,
                    "today_count": picks["today_count"] or 0
                },
                "active_symbols": active or 0,
                "server_time": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Freshness check failed: {e}")
        return {"error": str(e)}


@router.get("/data/stats", dependencies=[Depends(verify_admin_token)])
async def get_data_stats():
    """Get summary statistics for admin dashboard."""
    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            stocks = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE classification = 'ALL') as all_tier,
                    COUNT(*) FILTER (WHERE classification = 'ACTIVE') as active_tier
                FROM stock_universe
            """)

            shortlist = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE date = CURRENT_DATE) as today,
                    COUNT(*) as total
                FROM shortlist_candidates
            """)

            picks = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as today,
                    COUNT(*) as total
                FROM picks
            """)

            return {
                "stocks": {
                    "total_symbols": stocks["total"] or 0,
                    "all_tier": stocks["all_tier"] or 0,
                    "active_tier": stocks["active_tier"] or 0
                },
                "shortlist": {
                    "today": shortlist["today"] or 0,
                    "total": shortlist["total"] or 0
                },
                "picks": {
                    "today": picks["today"] or 0,
                    "total": picks["total"] or 0
                },
                "users": {"total": 0, "note": "Firebase auth not configured"}
            }
    except Exception as e:
        logger.error(f"Stats check failed: {e}")
        return {"error": str(e)}


# ========================= PIPELINE TRIGGERS =========================
@router.post("/trigger-prescreen", dependencies=[Depends(verify_admin_token)])
async def trigger_prescreen():
    """Trigger prescreen agent manually."""
    try:
        from app.services.agent_manager import get_agent_manager
        agent_manager = await get_agent_manager()
        result = await agent_manager.run_prescreen_agent()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Prescreen trigger failed: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/trigger-full-pipeline", dependencies=[Depends(verify_admin_token)])
async def trigger_full_pipeline():
    """Trigger entire daily pipeline (prescreen → charts → vision → social → arbitrator)."""
    try:
        # Import the async function directly since it's not a module
        import sys
        import os
        scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts")
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)
        from run_daily_pipeline import run_daily_pipeline
        result = await run_daily_pipeline()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Full pipeline trigger failed: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/build-active", dependencies=[Depends(verify_admin_token)])
async def build_active_symbols():
    """Rebuild ACTIVE tier from ALL stocks (volume > 100K, price > $1)."""
    try:
        from app.tasks.build_active_symbols import _build_active_async
        result = await _build_active_async()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Build active failed: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/prime-data", dependencies=[Depends(verify_admin_token)])
async def prime_data(mode: str = "catchup"):
    """Prime FMP data. mode=bootstrap (full 6mo) or catchup (delta from last date)."""
    try:
        if mode == "bootstrap":
            from app.tasks.fmp_bootstrap import _bootstrap_async
            result = await _bootstrap_async()
        else:
            from app.tasks.fmp_delta_update import _delta_update_async
            result = await _delta_update_async()
        return {"status": "success", "mode": mode, "result": result}
    except Exception as e:
        logger.error(f"Prime data failed: {e}")
        return {"status": "error", "error": str(e)}
