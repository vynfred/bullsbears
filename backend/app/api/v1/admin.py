# backend/app/api/v1/admin.py
"""
BullsBears Admin API - Secret admin endpoints
Only accessible via secret URL known to owner
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin credentials from environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "hellovynfred@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "bullsbears2025")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None


@router.post("/auth/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """Admin login - validates credentials"""
    if request.email == ADMIN_EMAIL and request.password == ADMIN_PASSWORD:
        # Simple token for now - in production use proper JWT
        return LoginResponse(
            success=True,
            message="Login successful",
            token="admin-session-token"
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/system/status")
async def get_system_status():
    """Get current system status"""
    try:
        from app.services.system_state import is_system_on
        system_on = await is_system_on()
        return {
            "system_on": system_on,
            "status": "ON" if system_on else "OFF"
        }
    except Exception as e:
        return {
            "system_on": False,
            "status": "ERROR",
            "error": str(e)
        }


@router.post("/system/on")
async def turn_system_on():
    """Turn system ON"""
    try:
        from app.services.system_state import set_system_on
        success = await set_system_on(True)
        if success:
            return {"success": True, "message": "System turned ON"}
        else:
            return {"success": False, "message": "Failed to set system state - Redis may be unavailable"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/system/off")
async def turn_system_off():
    """Turn system OFF"""
    try:
        from app.services.system_state import set_system_on
        success = await set_system_on(False)
        if success:
            return {"success": True, "message": "System turned OFF"}
        else:
            return {"success": False, "message": "Failed to set system state - Redis may be unavailable"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/health")
async def admin_health_check():
    """Check health of all services"""
    import httpx
    import os

    health = {
        "render": False,
        "fireworks": False,
        "database": False,
        "redis": False
    }

    # Check Render backend (self)
    health["render"] = True  # If we're responding, Render is up

    # Check Fireworks API
    fireworks_key = os.getenv("FIREWORKS_API_KEY")
    if fireworks_key:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.fireworks.ai/inference/v1/models",
                    headers={"Authorization": f"Bearer {fireworks_key}"}
                )
                health["fireworks"] = resp.status_code == 200
        except Exception:
            pass

    # Check Redis
    try:
        from app.services.system_state import _get_redis_client
        client = _get_redis_client()
        if client:
            await client.ping()
            health["redis"] = True
    except Exception:
        pass

    # Check Database (placeholder - add real check when DB is connected)
    db_url = os.getenv("DATABASE_URL")
    health["database"] = bool(db_url)

    return health


@router.post("/init-db")
async def init_database():
    """Initialize database tables - run this once before priming data"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Create stock_classifications table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_classifications (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL UNIQUE,
                    exchange VARCHAR(10) NOT NULL,
                    current_tier VARCHAR(20) NOT NULL,
                    price DECIMAL(10, 2),
                    market_cap BIGINT,
                    daily_volume BIGINT,
                    company_name VARCHAR(255),
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    last_qualified_date DATE,
                    qualified_days_count INTEGER DEFAULT 0,
                    selection_fatigue_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_classifications_tier ON stock_classifications(current_tier);
                CREATE INDEX IF NOT EXISTS idx_classifications_symbol ON stock_classifications(symbol);
                CREATE INDEX IF NOT EXISTS idx_classifications_updated ON stock_classifications(updated_at);
            """)

            # Create prime_ohlc_90d table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS prime_ohlc_90d (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    open_price DECIMAL(10, 2),
                    high_price DECIMAL(10, 2),
                    low_price DECIMAL(10, 2),
                    close_price DECIMAL(10, 2),
                    volume BIGINT,
                    adj_close DECIMAL(10, 2),
                    vwap DECIMAL(10, 2),
                    UNIQUE(symbol, date)
                )
            """)

            # Create indexes for prime_ohlc_90d
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlc_symbol ON prime_ohlc_90d(symbol);
                CREATE INDEX IF NOT EXISTS idx_ohlc_date ON prime_ohlc_90d(date);
            """)

        return {
            "success": True,
            "message": "Database tables created successfully",
            "tables": ["stock_classifications", "prime_ohlc_90d"]
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Database initialization failed: {str(e)}"
        }


@router.post("/prime-data")
async def prime_historical_data(mode: str = "catchup"):
    """
    Prime historical data from FMP API via Celery worker

    Modes:
    - catchup: 7-day catchup (fast, ~5 min)
    - bootstrap: Full 90-day bootstrap (slow, ~25 min, ~7.8 GB)

    Both modes run on the Celery worker to avoid HTTP timeout.
    """
    import os

    # Check FMP API key
    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        return {
            "success": False,
            "message": "FMP_API_KEY not configured in environment",
            "total_mb": 0
        }

    try:
        from app.tasks.fmp_bootstrap import fmp_bootstrap, fmp_catchup

        if mode == "bootstrap":
            # Queue bootstrap task to Celery worker
            task = fmp_bootstrap.delay()
            return {
                "success": True,
                "message": f"Bootstrap queued to worker (task_id: {task.id}). Monitor progress in Render worker logs.",
                "task_id": task.id,
                "total_mb": 0
            }
        else:
            # Queue catchup task to Celery worker
            task = fmp_catchup.delay()
            return {
                "success": True,
                "message": f"Catchup queued to worker (task_id: {task.id}). Monitor progress in Render worker logs.",
                "task_id": task.id,
                "total_mb": 0
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to queue task: {str(e)}",
            "total_mb": 0
        }


@router.get("/prime-status")
async def get_prime_status(task_id: str = None):
    """Check status of bootstrap/catchup task"""
    if not task_id:
        return {"status": "unknown", "message": "Provide task_id to check status"}

    try:
        from app.core.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)

        if result.state == "PENDING":
            return {"status": "pending", "message": "Task is queued, waiting for worker"}
        elif result.state == "STARTED":
            return {"status": "running", "message": "Task is running on worker"}
        elif result.state == "SUCCESS":
            return {"status": "complete", "message": "Task completed", "result": result.result}
        elif result.state == "FAILURE":
            return {"status": "failed", "message": f"Task failed: {result.result}"}
        else:
            return {"status": result.state, "message": f"Task state: {result.state}"}
    except Exception as e:
        return {"status": "error", "message": f"Error checking status: {str(e)}"}
