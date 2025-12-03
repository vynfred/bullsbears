# backend/app/api/v1/admin.py
"""
BullsBears Admin API - Secret admin endpoints
Only accessible via secret URL known to owner
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

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

            # Create picks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    confidence DECIMAL(5, 4) NOT NULL,
                    reasoning TEXT,
                    target_low DECIMAL(10, 2),
                    target_high DECIMAL(10, 2),
                    pick_context JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_picks_symbol ON picks(symbol);
                CREATE INDEX IF NOT EXISTS idx_picks_direction ON picks(direction);
                CREATE INDEX IF NOT EXISTS idx_picks_created ON picks(created_at);
            """)

            # Create shortlist_candidates table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS shortlist_candidates (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    price_at_selection DECIMAL(10, 2),
                    prescreen_score DECIMAL(5, 2),
                    technical_score DECIMAL(5, 2),
                    fundamental_score DECIMAL(5, 2),
                    sentiment_score DECIMAL(5, 2),
                    vision_flags JSONB,
                    social_score DECIMAL(5, 2),
                    was_picked BOOLEAN DEFAULT FALSE,
                    picked_direction VARCHAR(10),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(date, symbol)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shortlist_date ON shortlist_candidates(date);
                CREATE INDEX IF NOT EXISTS idx_shortlist_symbol ON shortlist_candidates(symbol);
                CREATE INDEX IF NOT EXISTS idx_shortlist_picked ON shortlist_candidates(was_picked);
            """)

            # Create pick_outcomes_detailed table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pick_outcomes_detailed (
                    id SERIAL PRIMARY KEY,
                    pick_id INTEGER REFERENCES picks(id),
                    symbol VARCHAR(10) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    entry_price DECIMAL(10, 2),
                    target_low DECIMAL(10, 2),
                    target_high DECIMAL(10, 2),
                    outcome VARCHAR(20) DEFAULT 'pending',
                    exit_price DECIMAL(10, 2),
                    max_gain_pct DECIMAL(6, 2),
                    days_to_peak INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_outcomes_pick ON pick_outcomes_detailed(pick_id);
                CREATE INDEX IF NOT EXISTS idx_outcomes_symbol ON pick_outcomes_detailed(symbol);
                CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON pick_outcomes_detailed(outcome);
            """)

        return {
            "success": True,
            "message": "Database tables created successfully",
            "tables": ["stock_classifications", "prime_ohlc_90d", "picks", "shortlist_candidates", "pick_outcomes_detailed"]
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



# ==================== DATA ENDPOINTS FOR ADMIN DASHBOARD ====================

@router.get("/data/stats")
async def get_dashboard_stats():
    """Get summary stats for admin dashboard"""
    try:
        from app.core.database import get_asyncpg_pool
        from datetime import datetime, timedelta

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Get stocks count
            stocks_count = await conn.fetchval("""
                SELECT COUNT(DISTINCT symbol) FROM prime_ohlc_90d
            """) or 0

            # Check if picks table exists and get count
            picks_count = 0
            picks_today = 0
            try:
                picks_count = await conn.fetchval("SELECT COUNT(*) FROM picks") or 0
                picks_today = await conn.fetchval("""
                    SELECT COUNT(*) FROM picks WHERE DATE(created_at) = CURRENT_DATE
                """) or 0
            except:
                pass

            # Get shortlist count
            shortlist_count = 0
            shortlist_today = 0
            try:
                shortlist_count = await conn.fetchval("SELECT COUNT(*) FROM shortlist_candidates") or 0
                shortlist_today = await conn.fetchval("""
                    SELECT COUNT(*) FROM shortlist_candidates WHERE date = CURRENT_DATE
                """) or 0
            except:
                pass

            # Get Firebase Auth user count
            users_count = 0
            try:
                from firebase_admin import auth
                # Iterate through users to count them (Firebase doesn't have a direct count API)
                page = auth.list_users()
                while page:
                    users_count += len(page.users)
                    page = page.get_next_page()
            except Exception as e:
                logger.warning(f"Could not count Firebase users: {e}")

            return {
                "stocks": {
                    "total_symbols": stocks_count,
                    "ohlc_rows": await conn.fetchval("SELECT COUNT(*) FROM prime_ohlc_90d") or 0
                },
                "picks": {
                    "total": picks_count,
                    "today": picks_today
                },
                "shortlist": {
                    "total": shortlist_count,
                    "today": shortlist_today
                },
                "users": {
                    "total": users_count
                }
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/data/picks")
async def get_picks_data(limit: int = 50, offset: int = 0):
    """Get picks for admin dashboard"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Check if table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'picks')
            """)
            if not exists:
                return {"picks": [], "total": 0, "message": "Picks table not created yet"}

            total = await conn.fetchval("SELECT COUNT(*) FROM picks") or 0
            rows = await conn.fetch("""
                SELECT id, symbol, direction, confidence, reasoning,
                       target_low, target_high, created_at
                FROM picks
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)

            picks = [{
                "id": r["id"],
                "symbol": r["symbol"],
                "direction": r["direction"],
                "confidence": float(r["confidence"]) * 100 if r["confidence"] else 0,
                "reasoning": r["reasoning"][:100] + "..." if r["reasoning"] and len(r["reasoning"]) > 100 else r["reasoning"],
                "target_low": float(r["target_low"]) if r["target_low"] else None,
                "target_high": float(r["target_high"]) if r["target_high"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            } for r in rows]

            return {"picks": picks, "total": total}
    except Exception as e:
        return {"error": str(e), "picks": [], "total": 0}


@router.get("/data/shortlist")
async def get_shortlist_data(limit: int = 50, offset: int = 0, date: str = None):
    """Get shortlist candidates for admin dashboard"""
    try:
        from app.core.database import get_asyncpg_pool
        from datetime import datetime

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'shortlist_candidates')
            """)
            if not exists:
                return {"shortlist": [], "total": 0, "message": "Shortlist table not created yet"}

            query = "SELECT COUNT(*) FROM shortlist_candidates"
            params = []
            if date:
                query += " WHERE date = $1"
                params.append(datetime.strptime(date, "%Y-%m-%d").date())

            total = await conn.fetchval(query, *params) or 0

            data_query = """
                SELECT id, date, symbol, price_at_selection, prescreen_score,
                       technical_score, sentiment_score, was_picked, picked_direction, created_at
                FROM shortlist_candidates
            """
            if date:
                data_query += " WHERE date = $1"
                data_query += " ORDER BY created_at DESC LIMIT $2 OFFSET $3"
                rows = await conn.fetch(data_query, datetime.strptime(date, "%Y-%m-%d").date(), limit, offset)
            else:
                data_query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
                rows = await conn.fetch(data_query, limit, offset)

            shortlist = [{
                "id": r["id"],
                "date": r["date"].isoformat() if r["date"] else None,
                "symbol": r["symbol"],
                "price": float(r["price_at_selection"]) if r["price_at_selection"] else None,
                "prescreen_score": float(r["prescreen_score"]) if r["prescreen_score"] else None,
                "technical_score": float(r["technical_score"]) if r["technical_score"] else None,
                "sentiment_score": float(r["sentiment_score"]) if r["sentiment_score"] else None,
                "was_picked": r["was_picked"],
                "picked_direction": r["picked_direction"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            } for r in rows]

            return {"shortlist": shortlist, "total": total}
    except Exception as e:
        return {"error": str(e), "shortlist": [], "total": 0}


@router.get("/data/stocks")
async def get_stocks_data(limit: int = 50, offset: int = 0, search: str = None):
    """Get stock data for admin dashboard"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Get unique symbols with latest data
            if search:
                total = await conn.fetchval("""
                    SELECT COUNT(DISTINCT symbol) FROM prime_ohlc_90d
                    WHERE symbol ILIKE $1
                """, f"%{search}%") or 0

                rows = await conn.fetch("""
                    SELECT DISTINCT ON (symbol) symbol, date, close_price, volume
                    FROM prime_ohlc_90d
                    WHERE symbol ILIKE $1
                    ORDER BY symbol, date DESC
                    LIMIT $2 OFFSET $3
                """, f"%{search}%", limit, offset)
            else:
                total = await conn.fetchval("SELECT COUNT(DISTINCT symbol) FROM prime_ohlc_90d") or 0
                rows = await conn.fetch("""
                    SELECT DISTINCT ON (symbol) symbol, date, close_price, volume
                    FROM prime_ohlc_90d
                    ORDER BY symbol, date DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)

            stocks = [{
                "symbol": r["symbol"],
                "last_date": r["date"].isoformat() if r["date"] else None,
                "close_price": float(r["close_price"]) if r["close_price"] else None,
                "volume": r["volume"]
            } for r in rows]

            return {"stocks": stocks, "total": total}
    except Exception as e:
        return {"error": str(e), "stocks": [], "total": 0}


@router.post("/trigger-pipeline")
async def trigger_full_pipeline():
    """Manually trigger the full daily pipeline"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.fmp_delta_update import fmp_delta_update
        task = fmp_delta_update.delay()

        return {
            "success": True,
            "message": f"Pipeline triggered (task_id: {task.id})",
            "task_id": task.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/trigger-prescreen")
async def trigger_prescreen():
    """Manually trigger the prescreen task (ACTIVE → SHORT_LIST)"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.run_prescreen import run_prescreen
        task = run_prescreen.delay()

        return {
            "success": True,
            "message": f"Prescreen triggered (task_id: {task.id})",
            "task_id": task.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/trigger-charts")
async def trigger_charts():
    """Manually trigger chart generation for SHORT_LIST"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.generate_charts import generate_charts
        task = generate_charts.delay()

        return {
            "success": True,
            "message": f"Chart generation triggered (task_id: {task.id})",
            "task_id": task.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/trigger-charts-sync")
async def trigger_charts_sync():
    """Run chart generation synchronously for debugging"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.generate_charts import get_chart_generator
        gen = await get_chart_generator()
        result = await gen.generate_all_charts()

        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@router.post("/trigger-vision")
async def trigger_vision():
    """Manually trigger Groq vision analysis on charts"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.run_groq_vision import run_groq_vision
        task = run_groq_vision.delay()

        return {
            "success": True,
            "message": f"Vision analysis triggered (task_id: {task.id})",
            "task_id": task.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/trigger-vision-sync")
async def trigger_vision_sync():
    """Run vision analysis synchronously for debugging"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.run_groq_vision import _run_vision
        result = await _run_vision()

        return {"success": True, "result": result}
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@router.get("/groq-models")
async def list_groq_models():
    """List available Groq models"""
    import os
    import httpx

    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return {"error": "GROQ_API_KEY not set"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"}
        )
        return resp.json()


@router.post("/test-vision")
async def test_vision():
    """Test Fireworks Vision API with a single chart - verbose debug"""
    import base64
    import httpx
    import json
    from pathlib import Path
    from app.core.database import get_asyncpg_pool
    from app.core.config import settings

    debug_info = {}

    # Check API key
    fireworks_key = settings.FIREWORKS_API_KEY
    debug_info["fireworks_key_set"] = bool(fireworks_key)
    debug_info["fireworks_key_prefix"] = fireworks_key[:10] + "..." if fireworks_key else None
    debug_info["model"] = "accounts/fireworks/models/qwen3-vl-30b-a3b-thinking"

    # Get one chart URL
    db = await get_asyncpg_pool()
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT symbol, chart_url FROM shortlist_candidates
            WHERE chart_url IS NOT NULL LIMIT 1
        """)

    if not row:
        return {"success": False, "message": "No charts found", "debug": debug_info}

    symbol = row["symbol"]
    chart_url = row["chart_url"]
    debug_info["symbol"] = symbol
    debug_info["chart_url"] = chart_url

    # Download image
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            img_resp = await client.get(chart_url)
            img_resp.raise_for_status()
            base64_png = base64.b64encode(img_resp.content).decode("utf-8")
            debug_info["image_downloaded"] = True
            debug_info["image_size_bytes"] = len(img_resp.content)
    except Exception as e:
        debug_info["image_error"] = str(e)
        return {"success": False, "message": "Image download failed", "debug": debug_info}

    # Load prompt
    prompt_path = Path(__file__).parent.parent.parent / "services" / "prompts" / "vision_prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    debug_info["prompt_loaded"] = True

    # Call Fireworks Vision (Qwen3-VL-30B-A3B)
    payload = {
        "model": "accounts/fireworks/models/qwen3-vl-30b-a3b-thinking",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Stock: {symbol}\n\n{prompt}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_png}"}}
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 2048,  # Thinking model needs more tokens for reasoning + JSON output
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.fireworks.ai/inference/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {fireworks_key}",
                    "Content-Type": "application/json"
                },
            )
            debug_info["fireworks_status"] = resp.status_code
            debug_info["fireworks_response"] = resp.text[:500]

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                debug_info["fireworks_content"] = content

                # Parse JSON - for thinking models, look after </think> tag
                json_content = content
                if "</think>" in content:
                    json_content = content.split("</think>")[-1].strip()

                # Find the last JSON object (most reliable for thinking models)
                start = json_content.rfind("{")
                end = json_content.rfind("}") + 1
                if start != -1 and end > 0:
                    flags = json.loads(json_content[start:end])
                    debug_info["parsed_flags"] = flags
                    return {"success": True, "flags": flags, "debug": debug_info}
                else:
                    return {"success": False, "message": "No JSON in response", "debug": debug_info}
            else:
                return {"success": False, "message": f"Fireworks error: {resp.status_code}", "debug": debug_info}
    except Exception as e:
        debug_info["fireworks_error"] = str(e)
        return {"success": False, "message": str(e), "debug": debug_info}


@router.get("/shortlist-status")
async def shortlist_status():
    """Check current shortlist status - vision and social completion"""
    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Get latest date
            row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
            if not row or not row['latest_date']:
                return {"success": False, "message": "No shortlist found"}

            latest_date = row['latest_date']

            # Get counts
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN direction = 'bull' THEN 1 END) as bullish,
                    COUNT(CASE WHEN direction = 'bear' THEN 1 END) as bearish,
                    COUNT(CASE WHEN vision_flags IS NOT NULL THEN 1 END) as has_vision,
                    COUNT(CASE WHEN social_score IS NOT NULL THEN 1 END) as has_social
                FROM shortlist_candidates
                WHERE date = $1
            """, latest_date)

            # Get sample with full social data
            sample = await conn.fetch("""
                SELECT symbol, direction, social_score, social_data,
                       vision_flags IS NOT NULL as has_vision
                FROM shortlist_candidates
                WHERE date = $1
                ORDER BY rank
                LIMIT 5
            """, latest_date)

            return {
                "success": True,
                "date": str(latest_date),
                "total": stats['total'],
                "bullish": stats['bullish'],
                "bearish": stats['bearish'],
                "has_vision": stats['has_vision'],
                "has_social": stats['has_social'],
                "sample": [dict(s) for s in sample]
            }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/trigger-social")
async def trigger_social():
    """Manually trigger Grok social/news analysis"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.run_grok_social import run_grok_social
        task = run_grok_social.delay()

        return {
            "success": True,
            "message": f"Social analysis triggered (task_id: {task.id})",
            "task_id": task.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/trigger-social-sync")
async def trigger_social_sync():
    """Run Grok social analysis synchronously (for debugging)"""
    import os

    debug_info = {
        "grok_key_set": bool(os.getenv("GROK_API_KEY")),
        "grok_key_prefix": os.getenv("GROK_API_KEY", "")[:10] + "..." if os.getenv("GROK_API_KEY") else None,
    }

    try:
        from app.services.system_state import is_system_on
        if not await is_system_on():
            return {"success": False, "message": "System is OFF", "debug": debug_info}

        # Get symbols from shortlist
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            symbols = await conn.fetch("""
                SELECT symbol FROM shortlist_candidates
                WHERE date = (SELECT MAX(date) FROM shortlist_candidates)
            """)

        if not symbols:
            return {"success": False, "message": "No symbols in shortlist", "debug": debug_info}

        debug_info["symbol_count"] = len(symbols)

        # Run social analysis directly
        from app.services.cloud_agents.social_agent import run_social_analysis
        results = await run_social_analysis([{"symbol": s["symbol"]} for s in symbols])

        # Count successful
        with_scores = sum(1 for r in results if r.get("social_score", 0) != 0)

        return {
            "success": True,
            "result": {
                "analyzed": len(results),
                "with_scores": with_scores
            },
            "debug": debug_info
        }
    except Exception as e:
        debug_info["error"] = str(e)
        return {"success": False, "message": str(e), "debug": debug_info}


@router.post("/test-grok")
async def test_grok():
    """Test Grok API with a single symbol - verbose debug"""
    import os
    import json
    import httpx
    from pathlib import Path

    debug_info = {
        "grok_key_set": bool(os.getenv("GROK_API_KEY")),
        "grok_key_prefix": os.getenv("GROK_API_KEY", "")[:10] + "..." if os.getenv("GROK_API_KEY") else None,
    }

    try:
        grok_key = os.getenv("GROK_API_KEY")
        if not grok_key:
            return {"success": False, "message": "GROK_API_KEY not set", "debug": debug_info}

        # Load prompt
        prompt_path = Path(__file__).parent.parent.parent / "services" / "prompts" / "social_prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8").strip()
        debug_info["prompt_loaded"] = True

        # Test with AAPL
        symbol = "AAPL"
        full_prompt = prompt.replace("{SYMBOL}", symbol)
        debug_info["test_symbol"] = symbol

        payload = {
            "model": "grok-4-fast-reasoning",
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.0,
            "max_tokens": 256,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {grok_key}"}
            )

            debug_info["grok_status"] = resp.status_code

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                debug_info["grok_raw_response"] = content

                # Try to parse JSON
                start = content.find("{")
                end = content.rfind("}") + 1
                if start != -1 and end > 0:
                    data = json.loads(content[start:end])
                    debug_info["parsed_data"] = data
                    return {"success": True, "data": data, "debug": debug_info}
                else:
                    return {"success": False, "message": "No JSON in response", "debug": debug_info}
            else:
                debug_info["grok_error"] = resp.text
                return {"success": False, "message": f"Grok API error: {resp.status_code}", "debug": debug_info}

    except Exception as e:
        debug_info["error"] = str(e)
        return {"success": False, "message": str(e), "debug": debug_info}


@router.post("/trigger-arbitrator")
async def trigger_arbitrator():
    """Manually trigger the arbitrator task (SHORT_LIST → PICKS)"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from app.tasks.run_arbitrator import run_arbitrator
        task = run_arbitrator.delay()

        return {
            "success": True,
            "message": f"Arbitrator triggered (task_id: {task.id})",
            "task_id": task.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/trigger-arbitrator-sync")
async def trigger_arbitrator_sync():
    """Run arbitrator synchronously (for debugging)"""
    import json

    debug_info = {}

    try:
        from app.services.system_state import is_system_on
        if not await is_system_on():
            return {"success": False, "message": "System is OFF", "debug": debug_info}

        # Get shortlist with all data
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Get latest shortlist date
            date_row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
            if not date_row or not date_row['latest_date']:
                return {"success": False, "message": "No shortlist found", "debug": debug_info}
            shortlist_date = date_row['latest_date']
            debug_info["shortlist_date"] = str(shortlist_date)

            shortlist = await conn.fetch("""
                SELECT symbol, rank, direction, prescreen_score, vision_flags, social_score
                FROM shortlist_candidates
                WHERE date = $1
                ORDER BY rank
                LIMIT 75
            """, shortlist_date)

        debug_info["shortlist_count"] = len(shortlist)

        if not shortlist:
            return {"success": False, "message": "Empty shortlist", "debug": debug_info}

        # Build phase_data for arbitrator
        phase_data = {
            "short_list": [dict(s) for s in shortlist],
            "vision_flags": {s["symbol"]: json.loads(s["vision_flags"]) if s["vision_flags"] else {} for s in shortlist},
            "social_scores": {s["symbol"]: float(s["social_score"]) if s["social_score"] else 0 for s in shortlist},
            "market_context": {},
        }

        # Call arbitrator
        from app.services.cloud_agents.arbitrator_agent import get_final_picks
        result = await get_final_picks(phase_data)

        debug_info["arbitrator_response"] = result

        # Handle both response formats: final_picks OR bullish_picks/bearish_picks
        final_picks = result.get("final_picks", [])
        if not final_picks:
            # Try bullish_picks + bearish_picks format
            bullish = result.get("bullish_picks", [])
            bearish = result.get("bearish_picks", [])
            for p in bullish:
                p["direction"] = "bullish"
                p["symbol"] = p.get("ticker") or p.get("symbol")
            for p in bearish:
                p["direction"] = "bearish"
                p["symbol"] = p.get("ticker") or p.get("symbol")
            final_picks = bullish + bearish

        if not final_picks:
            return {"success": False, "message": "No picks returned", "debug": debug_info}

        # Store picks with Fib-based targets
        from app.services.fib_calculator import get_fib_targets_for_symbol

        async with db.acquire() as conn:
            for pick in final_picks:
                symbol = pick.get("symbol") or pick.get("ticker")
                if not symbol:
                    continue
                direction = pick.get("direction", "bullish")

                # Get price from shortlist
                candidate = await conn.fetchrow("""
                    SELECT price_at_selection FROM shortlist_candidates
                    WHERE date = $1 AND symbol = $2
                """, shortlist_date, symbol)

                current_price = float(candidate['price_at_selection']) if candidate and candidate['price_at_selection'] else 0

                # Calculate Fib targets (no hallucination)
                fib_targets = await get_fib_targets_for_symbol(
                    symbol=symbol,
                    current_price=current_price,
                    direction=direction,
                    db_pool=db
                )

                # Use new confluence target attributes
                target_low = fib_targets.primary_target
                target_high = fib_targets.moonshot_target if fib_targets.moonshot_target else fib_targets.primary_target * 1.15

                # Store complete fib data including stop_loss and entry for pretty charts
                debug_info[f"fib_{symbol}"] = {
                    "price": current_price,
                    "entry_price": current_price,
                    "primary_target": target_low,
                    "moonshot_target": target_high,
                    "stop_loss": fib_targets.stop_loss,
                    "swing_low": fib_targets.swing_low,
                    "swing_high": fib_targets.swing_high,
                    "confluence_score": fib_targets.confluence_score,
                    "valid": fib_targets.valid
                }

                await conn.execute("""
                    INSERT INTO picks (
                        symbol, direction, confidence, reasoning,
                        target_low, target_high, primary_target, moonshot_target,
                        confluence_score,
                        pick_context, created_at, expires_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP + INTERVAL '30 days'
                    )
                """,
                    symbol,
                    direction,
                    float(pick.get("confidence", 0)) / 100.0 if pick.get("confidence", 0) > 1 else pick.get("confidence", 0.0),
                    pick.get("reasoning", ""),
                    target_low,  # target_low (legacy)
                    target_high,  # target_high (legacy)
                    target_low,  # primary_target
                    target_high if fib_targets.moonshot_target else None,  # moonshot_target
                    fib_targets.confluence_score,
                    json.dumps({"arbitrator": pick, "fib": debug_info[f"fib_{symbol}"]})
                )

                # Mark as picked
                await conn.execute("""
                    UPDATE shortlist_candidates
                    SET was_picked = TRUE, picked_direction = $1
                    WHERE date = $2 AND symbol = $3
                """, direction, shortlist_date, symbol)

        # Generate pretty charts for final picks (async, don't block)
        try:
            from app.tasks.generate_pretty_charts import generate_pretty_charts_for_picks
            chart_result = await generate_pretty_charts_for_picks()
            debug_info["pretty_charts"] = chart_result
        except Exception as chart_err:
            debug_info["pretty_charts_error"] = str(chart_err)

        return {
            "success": True,
            "picks_count": len(final_picks),
            "picks": final_picks,
            "debug": debug_info
        }
    except Exception as e:
        debug_info["error"] = str(e)
        import traceback
        debug_info["traceback"] = traceback.format_exc()
        return {"success": False, "message": str(e), "debug": debug_info}


@router.post("/trigger-pretty-charts")
async def trigger_pretty_charts():
    """Regenerate pretty charts for existing picks"""
    try:
        from app.tasks.generate_pretty_charts import generate_pretty_charts_for_picks
        result = await generate_pretty_charts_for_picks()
        return {"success": True, "result": result}
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@router.post("/migrate-confluence")
async def migrate_confluence_columns():
    """Add confluence columns to picks and pick_outcomes_detailed tables"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Add columns to picks table
            picks_columns = [
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS confluence_score SMALLINT DEFAULT 0",
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS confluence_methods TEXT[] DEFAULT '{}'",
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS rsi_divergence BOOLEAN DEFAULT FALSE",
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS primary_target NUMERIC(10, 2)",
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS moonshot_target NUMERIC(10, 2)",
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS gann_alignment BOOLEAN DEFAULT FALSE",
                "ALTER TABLE picks ADD COLUMN IF NOT EXISTS weekly_pivots JSONB",
            ]

            for sql in picks_columns:
                await conn.execute(sql)

            # Add columns to pick_outcomes_detailed table
            outcomes_columns = [
                "ALTER TABLE pick_outcomes_detailed ADD COLUMN IF NOT EXISTS confluence_score SMALLINT",
                "ALTER TABLE pick_outcomes_detailed ADD COLUMN IF NOT EXISTS hit_primary_target BOOLEAN DEFAULT FALSE",
                "ALTER TABLE pick_outcomes_detailed ADD COLUMN IF NOT EXISTS hit_moonshot_target BOOLEAN DEFAULT FALSE",
                "ALTER TABLE pick_outcomes_detailed ADD COLUMN IF NOT EXISTS primary_target NUMERIC(10, 2)",
                "ALTER TABLE pick_outcomes_detailed ADD COLUMN IF NOT EXISTS moonshot_target NUMERIC(10, 2)",
            ]

            for sql in outcomes_columns:
                await conn.execute(sql)

            return {
                "success": True,
                "message": "Confluence columns added successfully",
                "picks_columns_added": len(picks_columns),
                "outcomes_columns_added": len(outcomes_columns)
            }
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@router.post("/clear-picks")
async def clear_all_picks():
    """Clear ALL picks data - complete reset"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Clear pick_outcomes_detailed first (foreign key)
            outcomes_deleted = await conn.execute("DELETE FROM pick_outcomes_detailed")

            # Clear picks table
            picks_deleted = await conn.execute("DELETE FROM picks")

            return {
                "success": True,
                "message": "All picks cleared successfully",
                "picks_deleted": picks_deleted,
                "outcomes_deleted": outcomes_deleted
            }
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@router.post("/trigger-outcome-monitor")
async def trigger_outcome_monitor():
    """
    Manually trigger the pick outcome monitor.
    Checks all active picks for target hits and updates summaries.
    """
    try:
        from app.tasks.monitor_pick_outcomes import _monitor_outcomes
        from app.services.system_state import is_system_on

        # Check if system is on
        if not await is_system_on():
            return {"success": False, "message": "System is OFF"}

        # Run the async function directly (we're already in async context)
        result = await _monitor_outcomes()
        return {
            "success": True,
            "message": "Outcome monitor completed",
            "result": result
        }
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@router.post("/trigger-full-pipeline")
async def trigger_full_pipeline_sequence():
    """Trigger the complete AI pipeline: Prescreen → Charts → Vision → Social → Arbitrator"""
    try:
        from app.services.system_state import is_system_on

        if not await is_system_on():
            return {"success": False, "message": "System is OFF. Turn it ON first."}

        from celery import chain
        from app.tasks.run_prescreen import run_prescreen
        from app.tasks.generate_charts import generate_charts
        from app.tasks.run_groq_vision import run_groq_vision
        from app.tasks.run_grok_social import run_grok_social
        from app.tasks.run_arbitrator import run_arbitrator

        # Chain all tasks in sequence
        pipeline = chain(
            run_prescreen.s(),
            generate_charts.s(),
            run_groq_vision.s(),
            run_grok_social.s(),
            run_arbitrator.s()
        )
        result = pipeline.apply_async()

        return {
            "success": True,
            "message": "Full pipeline triggered: Prescreen → Charts → Vision → Social → Arbitrator",
            "task_id": result.id,
            "pipeline_steps": ["prescreen", "charts", "vision", "social", "arbitrator"]
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}