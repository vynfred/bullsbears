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

