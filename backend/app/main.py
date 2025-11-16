#!/usr/bin/env python3
"""
BullsBears Backend – FINAL v3.3 (November 12, 2025)
Minimal FastAPI for health + Firebase + badges
"""

import logging
from datetime import datetime
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
    """
    Startup event handler - initialize connections
    Note: We allow the app to start even if some services fail,
    so Cloud Run health checks can still work
    """
    import sys

    # Try to initialize database
    try:
        await init_db()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        # Print to stderr for Cloud Run logs
        print(f"ERROR: Database connection failed: {e}", file=sys.stderr)
        # Re-raise to fail startup if database is critical
        raise

    # Try to initialize Redis (optional)
    try:
        await redis_client.connect()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed (non-critical): {e}")

    logger.info("🚀 BullsBears v3.3 API ready")

@app.on_event("shutdown")
async def shutdown():
    await close_db()
    await redis_client.disconnect()

@app.get("/")
async def root():
    return {"message": "BullsBears v3.3 API", "version": "3.3.0"}

@app.get("/health")
async def health():
    """
    Health check endpoint for Cloud Run startup probes
    Returns 200 if all critical services are accessible
    """
    from .core.database import get_asyncpg_pool
    from .services.push_picks_to_firebase import FirebaseService

    health_status = {
        "status": "healthy",
        "version": "3.3.0",
        "checks": {}
    }

    # Check database connection
    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
        logger.error(f"Health check - Database error: {e}")

    # Check Redis connection (optional - don't fail health check if Redis is down)
    try:
        if redis_client.client:
            await redis_client.ping()
            health_status["checks"]["redis"] = "connected"
        else:
            health_status["checks"]["redis"] = "not_configured"
    except Exception as e:
        health_status["checks"]["redis"] = f"warning: {str(e)}"
        logger.warning(f"Health check - Redis warning: {e}")

    # Check Firebase connection (optional - don't fail health check)
    try:
        async with FirebaseService() as fb:
            await fb.get_data("/system/state")
        health_status["checks"]["firebase"] = "connected"
    except Exception as e:
        health_status["checks"]["firebase"] = f"warning: {str(e)}"
        logger.warning(f"Health check - Firebase warning: {e}")

    # Return 503 if unhealthy (tells Cloud Run to not route traffic)
    if health_status["status"] == "unhealthy":
        from fastapi import Response
        return Response(
            content=str(health_status),
            status_code=503,
            media_type="application/json"
        )

    return health_status

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

@app.post("/api/v1/admin/prime-data-test")
async def prime_data_test():
    """
    TEST: Prime database with 22 stocks to verify everything works
    """
    from .services.system_state import SystemState
    from .services.fmp_data_ingestion import get_fmp_ingestion
    from .core.database import get_asyncpg_pool

    try:
        # Check if system is already ON
        system_state = await SystemState.get_state()
        if system_state.get("status") == "ON":
            return {
                "success": False,
                "message": "Cannot prime data while system is ON. Turn system OFF first.",
                "status": "ON"
            }

        logger.info("🧪 Starting TEST data priming (22 stocks)...")

        # Get FMP ingestion service
        fmp = await get_fmp_ingestion()

        # Get first 22 NASDAQ symbols
        symbols = await fmp._get_nasdaq_symbols()
        test_symbols = symbols[:22]

        logger.info(f"Testing with symbols: {', '.join(test_symbols)}")

        # Fetch data for 22 stocks
        await fmp._fetch_90d_batch(test_symbols)

        # Verify data was actually stored
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM prime_ohlc_90d WHERE symbol = ANY($1)",
                test_symbols
            )
            unique_symbols = await conn.fetchval(
                "SELECT COUNT(DISTINCT symbol) FROM prime_ohlc_90d WHERE symbol = ANY($1)",
                test_symbols
            )

        logger.info(f"✅ Test complete! Stored {count} records for {unique_symbols} symbols")

        return {
            "success": True,
            "message": f"Test successful - {count} records stored for {unique_symbols}/22 symbols",
            "records_stored": count,
            "symbols_stored": unique_symbols,
            "symbols_tested": test_symbols,
            "data_mb": round(fmp.daily_mb, 3)
        }

    except Exception as e:
        logger.error(f"Test priming failed: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.get("/api/v1/admin/learner/reports")
async def get_learner_reports():
    """
    Get list of all learner reports with metadata
    Returns: [{date, path, size, generated_at}, ...]
    """
    from pathlib import Path
    import json

    try:
        insights_dir = Path(__file__).parent / "templates" / "insights"
        if not insights_dir.exists():
            return {"reports": []}

        reports = []
        for report_file in sorted(insights_dir.glob("learner_report_*.json"), reverse=True):
            try:
                data = json.loads(report_file.read_text())
                reports.append({
                    "date": report_file.stem.replace("learner_report_", ""),
                    "path": str(report_file.name),
                    "size": report_file.stat().st_size,
                    "generated_at": data.get("generated_at", ""),
                    "cycle_start": data.get("cycle_start", ""),
                    "cycle_end": data.get("cycle_end", ""),
                    "total_candidates": data.get("total_candidates", 0),
                    "final_picks": data.get("final_picks", 0)
                })
            except Exception as e:
                logger.error(f"Error reading report {report_file}: {e}")
                continue

        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        logger.error(f"Error listing learner reports: {e}")
        return {"error": str(e), "reports": []}

@app.get("/api/v1/admin/learner/reports/{date}")
async def get_learner_report(date: str):
    """
    Get specific learner report by date (format: YYYY-MM-DD)
    Returns: Full report JSON
    """
    from pathlib import Path
    import json

    try:
        insights_dir = Path(__file__).parent / "templates" / "insights"
        report_file = insights_dir / f"learner_report_{date}.json"

        if not report_file.exists():
            return {"error": f"Report not found for date {date}"}

        data = json.loads(report_file.read_text())
        return data
    except Exception as e:
        logger.error(f"Error reading learner report for {date}: {e}")
        return {"error": str(e)}

# ============================================
# ADMIN ENDPOINTS - RunPod Monitoring
# ============================================

@app.get("/api/v1/admin/runpod/status")
async def get_runpod_status():
    """
    Get RunPod worker status and cost information
    CRITICAL: This endpoint must NOT trigger RunPod startup
    """
    import os
    import httpx

    try:
        runpod_api_key = os.getenv("RUNPOD_API_KEY")
        endpoint_id = "0bv1yn1beqszt7"  # Your RunPod endpoint

        if not runpod_api_key:
            return {
                "error": "RunPod API key not configured",
                "workers_active": 0,
                "status": "not_configured"
            }

        # Query RunPod API for endpoint status (read-only, no worker start)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.runpod.io/v2/{endpoint_id}/status",
                headers={"Authorization": f"Bearer {runpod_api_key}"},
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                return {
                    "endpoint_id": endpoint_id,
                    "workers_active": data.get("workers", {}).get("running", 0),
                    "workers_idle": data.get("workers", {}).get("idle", 0),
                    "jobs_queued": data.get("jobs", {}).get("queued", 0),
                    "jobs_running": data.get("jobs", {}).get("running", 0),
                    "status": "healthy" if data.get("workers", {}).get("running", 0) == 0 else "active",
                    "cost_per_hour": 2.00,  # $2/hour for GPU
                    "estimated_daily_cost": data.get("workers", {}).get("running", 0) * 2.00 * 24,
                    "last_checked": datetime.now().isoformat()
                }
            else:
                return {
                    "error": f"RunPod API returned {response.status_code}",
                    "workers_active": 0,
                    "status": "error"
                }

    except Exception as e:
        logger.error(f"Failed to check RunPod status: {e}")
        return {
            "error": str(e),
            "workers_active": 0,
            "status": "error"
        }

@app.post("/api/v1/admin/runpod/emergency-shutdown")
async def emergency_shutdown_runpod():
    """
    EMERGENCY: Terminate all RunPod workers immediately
    Use this if workers are stuck or costs are running away
    """
    import os
    import httpx

    try:
        runpod_api_key = os.getenv("RUNPOD_API_KEY")
        endpoint_id = "0bv1yn1beqszt7"

        if not runpod_api_key:
            return {"success": False, "error": "RunPod API key not configured"}

        # Cancel all running jobs
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.runpod.io/v2/{endpoint_id}/cancel",
                headers={"Authorization": f"Bearer {runpod_api_key}"},
                json={"cancel_all": True},
                timeout=30.0
            )

            if response.status_code == 200:
                logger.warning("🚨 EMERGENCY SHUTDOWN: All RunPod workers terminated by admin")
                return {
                    "success": True,
                    "message": "All RunPod workers terminated",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"RunPod API returned {response.status_code}",
                    "response": response.text
                }

    except Exception as e:
        logger.error(f"Emergency shutdown failed: {e}")
        return {"success": False, "error": str(e)}

# ============================================
# ADMIN ENDPOINTS - Database Health
# ============================================

@app.get("/api/v1/admin/database/health")
async def get_database_health():
    """
    Get database health metrics: connection status, table counts, last updates
    """
    from .core.database import get_asyncpg_pool

    try:
        db = await get_asyncpg_pool()

        # Get table record counts
        tables = [
            "stock_classifications",
            "prime_ohlc_90d",
            "shortlist_candidates",
            "picks",
            "watchlist",
            "feature_weights",
            "agent_weights",
            "learning_cycles",
            "prompt_examples"
        ]

        table_counts = {}
        for table in tables:
            try:
                count = await db.fetchval(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = count
            except Exception as e:
                table_counts[table] = f"error: {str(e)}"

        # Get last data updates
        last_updates = {}
        try:
            last_pick = await db.fetchrow("SELECT MAX(created_at) as last_pick FROM picks")
            last_updates["last_pick"] = last_pick["last_pick"].isoformat() if last_pick and last_pick["last_pick"] else "never"
        except:
            last_updates["last_pick"] = "error"

        try:
            last_candidate = await db.fetchrow("SELECT MAX(date) as last_candidate FROM shortlist_candidates")
            last_updates["last_candidate"] = last_candidate["last_candidate"].isoformat() if last_candidate and last_candidate["last_candidate"] else "never"
        except:
            last_updates["last_candidate"] = "error"

        try:
            last_learning = await db.fetchrow("SELECT MAX(cycle_date) as last_learning FROM learning_cycles")
            last_updates["last_learning"] = last_learning["last_learning"].isoformat() if last_learning and last_learning["last_learning"] else "never"
        except:
            last_updates["last_learning"] = "error"

        # Get database size
        try:
            db_size = await db.fetchval("SELECT pg_database_size(current_database())")
            db_size_mb = round(db_size / (1024 * 1024), 2) if db_size else 0
        except:
            db_size_mb = "error"

        return {
            "connected": True,
            "table_counts": table_counts,
            "last_updates": last_updates,
            "database_size_mb": db_size_mb,
            "status": "healthy"
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "connected": False,
            "error": str(e),
            "status": "error"
        }

# ============================================
# ADMIN ENDPOINTS - API Usage Tracking
# ============================================

@app.get("/api/v1/admin/api-usage")
async def get_api_usage():
    """
    Get API usage statistics for all external services
    """
    from .core.redis_client import redis_client

    try:
        # Get usage from Redis cache (updated by tasks)
        fmp_usage = await redis_client.get("api_usage:fmp:today") or "0"
        groq_usage = await redis_client.get("api_usage:groq:today") or "0"
        grok_usage = await redis_client.get("api_usage:grok:today") or "0"

        return {
            "fmp": {
                "calls_today": int(fmp_usage),
                "limit_daily": 18000,  # 300 calls/min * 60 min = 18,000/hour (premium)
                "percentage": round((int(fmp_usage) / 18000) * 100, 2),
                "status": "healthy" if int(fmp_usage) < 14400 else "warning"  # 80% threshold
            },
            "groq": {
                "calls_today": int(groq_usage),
                "limit_daily": 14400,  # Free tier
                "percentage": round((int(groq_usage) / 14400) * 100, 2),
                "status": "healthy" if int(groq_usage) < 11520 else "warning"
            },
            "grok": {
                "calls_today": int(grok_usage),
                "limit_daily": 10000,  # Estimate
                "percentage": round((int(grok_usage) / 10000) * 100, 2),
                "status": "healthy" if int(grok_usage) < 8000 else "warning"
            },
            "runpod": {
                "gpu_hours_today": 0,  # TODO: Calculate from job logs
                "estimated_cost_today": 0,
                "status": "healthy"
            }
        }

    except Exception as e:
        logger.error(f"API usage check failed: {e}")
        return {"error": str(e)}

# ============================================
# ADMIN ENDPOINTS - User Metrics
# ============================================

@app.get("/api/v1/admin/users")
async def get_user_metrics():
    """
    Get user metrics from Firebase Auth and database
    """
    from .core.database import get_asyncpg_pool

    try:
        db = await get_asyncpg_pool()

        # Get watchlist stats
        total_watchlist = await db.fetchval("SELECT COUNT(*) FROM watchlist")
        unique_users = await db.fetchval("SELECT COUNT(DISTINCT user_id) FROM watchlist")

        # Get most watched stocks
        top_stocks = await db.fetch("""
            SELECT symbol, COUNT(*) as watch_count
            FROM watchlist
            GROUP BY symbol
            ORDER BY watch_count DESC
            LIMIT 5
        """)

        return {
            "total_users": unique_users or 0,  # From watchlist (Firebase Auth not directly accessible)
            "active_users_24h": 0,  # TODO: Track from Firebase Auth
            "new_signups_today": 0,  # TODO: Track from Firebase Auth
            "watchlist_entries": total_watchlist or 0,
            "gut_check_votes": 0,  # TODO: Implement when gut check is added
            "top_watched_stocks": [
                {"symbol": row["symbol"], "count": row["watch_count"]}
                for row in top_stocks
            ],
            "status": "partial"  # Partial data (no Firebase Auth access yet)
        }

    except Exception as e:
        logger.error(f"User metrics check failed: {e}")
        return {"error": str(e)}

# ============================================
# ADMIN ENDPOINTS - System Logs
# ============================================

@app.get("/api/v1/admin/logs")
async def get_system_logs(level: str = "INFO", limit: int = 100):
    """
    Get recent system logs
    Args:
        level: Log level filter (INFO, WARNING, ERROR)
        limit: Number of logs to return (max 500)
    """
    from pathlib import Path

    try:
        # Read from log file (if exists)
        log_file = Path("/var/log/bullsbears/app.log")  # Cloud Run log path

        if not log_file.exists():
            # Fallback to local log path
            log_file = Path(__file__).parent.parent / "logs" / "app.log"

        if not log_file.exists():
            return {
                "logs": [],
                "message": "Log file not found - logs may be in Cloud Logging",
                "cloud_logging_url": "https://console.cloud.google.com/logs"
            }

        # Read last N lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines

        # Filter by level
        filtered_logs = []
        for line in recent_lines:
            if level.upper() in line:
                filtered_logs.append(line.strip())

        return {
            "logs": filtered_logs,
            "count": len(filtered_logs),
            "level_filter": level,
            "total_lines": len(recent_lines)
        }

    except Exception as e:
        logger.error(f"Log retrieval failed: {e}")
        return {"error": str(e)}

# ============================================
# ADMIN ENDPOINTS - Manual Task Triggers
# ============================================

@app.post("/api/v1/admin/tasks/trigger/{task_name}")
async def trigger_manual_task(task_name: str):
    """
    Manually trigger a specific task
    Args:
        task_name: prescreen, arbitrator, learner, sync_firebase, etc.
    """
    from .services.system_state import SystemState

    try:
        # Check if system is ON
        if not await SystemState.is_system_on():
            return {
                "success": False,
                "error": "System is OFF - turn system ON before triggering tasks"
            }

        # Map task names to Celery tasks
        task_map = {
            "prescreen": "tasks.run_prescreen",
            "arbitrator": "tasks.run_arbitrator",
            "learner": "tasks.run_weekly_learner",
            "sync_firebase": "tasks.publish_to_firebase",
            "fmp_update": "tasks.fmp_delta_update",
            "build_active": "tasks.build_active_symbols",
            "generate_charts": "tasks.generate_charts",
            "vision": "tasks.run_groq_vision",
            "social": "tasks.run_grok_social"
        }

        if task_name not in task_map:
            return {
                "success": False,
                "error": f"Unknown task: {task_name}. Available: {list(task_map.keys())}"
            }

        # Trigger task asynchronously
        from .core.celery import celery_app
        task = celery_app.send_task(task_map[task_name])

        logger.info(f"🔧 Manual task triggered: {task_name} (task_id: {task.id})")

        return {
            "success": True,
            "task_name": task_name,
            "task_id": task.id,
            "message": f"Task {task_name} triggered successfully"
        }

    except Exception as e:
        logger.error(f"Manual task trigger failed: {e}")
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

from .api.v1 import stocks, watchlist, analytics

app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
