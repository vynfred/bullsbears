#!/usr/bin/env python3
"""
FRED Economic Calendar Fetcher
Runs daily at 4:30 AM ET (after Finnhub short interest)
120 API calls/min limit - plenty for our needs
"""

import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_asyncpg_pool
from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"

# High-impact economic releases we care about
HIGH_IMPACT_RELEASES = {
    10: "CPI",                    # Consumer Price Index
    11: "Employment Situation",   # Jobs report (NFP)
    21: "GDP",                    # Gross Domestic Product
    46: "FOMC",                   # Fed rate decisions
    86: "Retail Sales",
    50: "Industrial Production",
    53: "Housing Starts",
    312: "ISM Manufacturing",
    313: "ISM Services",
}


async def _fetch_fred_calendar_async():
    """
    Async function to fetch upcoming economic events from FRED.
    Called by both Celery task and daily pipeline.
    """
    if not await is_system_on():
        logger.info("⏸️ System is OFF - skipping FRED calendar fetch")
        return {"skipped": True, "reason": "system_off"}
    
    api_key = settings.FRED_API_KEY
    if not api_key:
        logger.warning("FRED_API_KEY not set - skipping economic calendar")
        return {"success": False, "error": "no_api_key"}
    
    db = await get_asyncpg_pool()
    
    # Ensure table exists
    async with db.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS economic_calendar (
                id SERIAL PRIMARY KEY,
                release_id INTEGER NOT NULL,
                release_name VARCHAR(100) NOT NULL,
                release_date DATE NOT NULL,
                impact_level VARCHAR(20) DEFAULT 'high',
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(release_id, release_date)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_econ_calendar_date ON economic_calendar(release_date)
        """)
    
    logger.info("📅 Fetching FRED economic calendar...")
    
    # Fetch next 14 days of release dates
    today = datetime.now().date()
    end_date = today + timedelta(days=14)
    
    events = []
    errors = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for release_id, release_name in HIGH_IMPACT_RELEASES.items():
            try:
                resp = await client.get(
                    f"{FRED_BASE}/release/dates",
                    params={
                        "release_id": release_id,
                        "api_key": api_key,
                        "file_type": "json",
                        "realtime_start": today.isoformat(),
                        "realtime_end": end_date.isoformat(),
                        "include_release_dates_with_no_data": "false"
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    dates = data.get("release_dates", [])
                    for d in dates:
                        events.append({
                            "release_id": release_id,
                            "release_name": release_name,
                            "release_date": d.get("date"),
                            "impact_level": "high"
                        })
                else:
                    logger.debug(f"FRED API error for {release_name}: {resp.status_code}")
                    errors += 1
                    
            except Exception as e:
                logger.debug(f"Error fetching {release_name}: {e}")
                errors += 1
            
            # Small delay to stay well under rate limit
            await asyncio.sleep(0.5)
    
    # Store events
    if events:
        async with db.acquire() as conn:
            for event in events:
                if event["release_date"]:
                    await conn.execute("""
                        INSERT INTO economic_calendar (release_id, release_name, release_date, impact_level, updated_at)
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                        ON CONFLICT (release_id, release_date) DO UPDATE SET
                            release_name = EXCLUDED.release_name,
                            updated_at = CURRENT_TIMESTAMP
                    """, event["release_id"], event["release_name"], event["release_date"], event["impact_level"])
            
            # Clean old events (older than 7 days)
            await conn.execute("""
                DELETE FROM economic_calendar WHERE release_date < CURRENT_DATE - INTERVAL '7 days'
            """)
    
    logger.info(f"✅ FRED calendar complete: {len(events)} events, {errors} errors")
    return {
        "success": True,
        "events_found": len(events),
        "errors": errors
    }


@celery_app.task(name="tasks.fetch_fred_calendar", bind=True, soft_time_limit=300, time_limit=360)
def fetch_fred_calendar(self):
    """Daily Celery task to fetch FRED economic calendar"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_fetch_fred_calendar_async())
    finally:
        loop.close()

