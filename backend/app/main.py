#!/usr/bin/env python3
"""
BullsBears Backend – FINAL v3.3 (November 12, 2025)
Minimal FastAPI for health + Firebase + badges
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .core.config import settings
from .core.database import init_db, close_db
from .core.redis_client import redis_client
# from .services.statistics_service import StatisticsService  # TODO: Implement when needed

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="BullsBears v3.3",
    version="3.3.0",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()
    await redis_client.connect()
    logger.info("BullsBears v3.3 API ready")

@app.on_event("shutdown")
async def shutdown():
    await close_db()
    await redis_client.disconnect()

@app.get("/")
async def root():
    return {"message": "BullsBears v3.3 API", "version": "3.3.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.3.0"}

# TODO: Implement StatisticsService for badge data
# @app.get("/api/v1/badge-data")
# async def get_badge_data():
#     stats = StatisticsService()
#     return await stats.refresh_badge_data()

@app.get("/api/v1/picks/latest")
async def get_latest_picks():
    from .services.push_picks_to_firebase import FirebaseService
    async with FirebaseService() as fb:
        data = await fb.get_latest_picks()
        return data or {"picks": []}

# ============================================
# ADMIN ENDPOINTS - System Control
# ============================================

@app.get("/api/v1/admin/status")
async def get_admin_status():
    """
    Get comprehensive system status for admin panel
    Returns database connections, API status, system state, etc.
    """
    from .services.system_state import SystemState
    from .core.database import engine
    from .core.redis_client import redis_client

    try:
        # Get system state
        system_state = await SystemState.get_state()

        # Check database connection
        db_connected = False
        try:
            if engine:
                db_connected = True
        except:
            pass

        # Check Redis connection
        redis_connected = await redis_client.ping() if redis_client else False

        # Check Firebase connection
        firebase_connected = False
        try:
            from .services.push_picks_to_firebase import FirebaseService
            async with FirebaseService() as fb:
                test_data = await fb.get_data("/system/state")
                firebase_connected = True
        except:
            pass

        return {
            "system": {
                "status": system_state.get("status", "OFF"),
                "data_primed": system_state.get("data_primed", False),
                "last_updated": system_state.get("last_updated"),
                "updated_by": system_state.get("updated_by")
            },
            "databases": {
                "google_sql": {"connected": db_connected, "status": "healthy" if db_connected else "disconnected"},
                "firebase": {"connected": firebase_connected, "status": "healthy" if firebase_connected else "disconnected"},
                "redis": {"connected": redis_connected, "status": "healthy" if redis_connected else "disconnected"}
            },
            "apis": {
                "fmp": {"status": "not_checked"},
                "groq": {"status": "not_checked"},
                "grok": {"status": "not_checked"},
                "deepseek": {"status": "not_checked"}
            },
            "runpod": {
                "endpoint": "0bv1yn1beqszt7",
                "status": "not_checked"
            }
        }

    except Exception as e:
        logger.error(f"Admin status check failed: {str(e)}")
        return {"error": str(e)}

@app.post("/api/v1/admin/system/on")
async def turn_system_on():
    """Turn system ON - enables all automated tasks"""
    from .services.system_state import SystemState

    try:
        success = await SystemState.set_state("ON", updated_by="admin")

        if success:
            logger.info("🟢 System turned ON by admin")
            return {
                "success": True,
                "message": "System is now ON - automated tasks enabled",
                "status": "ON"
            }
        else:
            return {
                "success": False,
                "message": "Failed to turn system ON",
                "status": "UNKNOWN"
            }

    except Exception as e:
        logger.error(f"Failed to turn system ON: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/api/v1/admin/system/off")
async def turn_system_off():
    """Turn system OFF - disables all automated tasks"""
    from .services.system_state import SystemState

    try:
        success = await SystemState.set_state("OFF", updated_by="admin")

        if success:
            logger.info("🔴 System turned OFF by admin")
            return {
                "success": True,
                "message": "System is now OFF - automated tasks disabled",
                "status": "OFF"
            }
        else:
            return {
                "success": False,
                "message": "Failed to turn system OFF",
                "status": "UNKNOWN"
            }

    except Exception as e:
        logger.error(f"Failed to turn system OFF: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/api/v1/admin/prime-data")
async def prime_data():
    """
    Prime database with 90 days of OHLC data for all NASDAQ stocks
    This is a one-time setup operation that should be run before turning system ON
    """
    from .services.system_state import SystemState
    from .services.fmp_data_ingestion import get_fmp_ingestion

    try:
        # Check if system is already ON
        system_state = await SystemState.get_state()
        if system_state.get("status") == "ON":
            return {
                "success": False,
                "message": "Cannot prime data while system is ON. Turn system OFF first.",
                "status": "ON"
            }

        logger.info("🔄 Starting data priming process...")

        # Get FMP ingestion service
        fmp = await get_fmp_ingestion()

        # Run bootstrap (this will take a while - ~7 weeks of data for ~6,960 stocks)
        await fmp.bootstrap_prime_db()

        # Mark data as primed
        await SystemState.mark_data_primed(True)

        logger.info("✅ Data priming complete!")

        return {
            "success": True,
            "message": "Data priming complete - 90 days OHLC loaded for all NASDAQ stocks",
            "data_primed": True,
            "total_mb": fmp.daily_mb
        }

    except Exception as e:
        logger.error(f"Data priming failed: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)