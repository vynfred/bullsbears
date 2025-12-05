#!/usr/bin/env python3
"""
Finnhub Short Interest Fetcher
Runs daily at 4:00 AM ET (after FMP delta update)
60 API calls/min limit → ~50 min for 3,000 ACTIVE stocks
"""

import asyncio
import httpx
import logging
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_asyncpg_pool
from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
RATE_LIMIT = 55  # Stay under 60/min


async def _fetch_short_interest_async():
    """
    Async function to fetch short interest for ACTIVE stocks.
    Called by both Celery task and daily pipeline.
    """
    if not await is_system_on():
        logger.info("⏸️ System is OFF - skipping short interest fetch")
        return {"skipped": True, "reason": "system_off"}

    api_key = settings.FINNHUB_API_KEY
    if not api_key:
        logger.error("FINNHUB_API_KEY not set")
        return {"success": False, "error": "no_api_key"}

    db = await get_asyncpg_pool()

    # Get ACTIVE symbols
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT symbol FROM stock_classifications
            WHERE current_tier IN ('ACTIVE', 'SHORT_LIST', 'PICKS')
        """)
        symbols = [r['symbol'] for r in rows]

    if not symbols:
        logger.warning("No ACTIVE stocks found")
        return {"success": False, "error": "no_stocks"}

    logger.info(f"📊 Fetching short interest for {len(symbols)} ACTIVE stocks")

    results = {}
    errors = 0
    calls_this_minute = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, symbol in enumerate(symbols):
            # Rate limiting - max 55 calls per minute
            now = asyncio.get_event_loop().time()
            calls_this_minute = [t for t in calls_this_minute if now - t < 60]

            if len(calls_this_minute) >= RATE_LIMIT:
                sleep_time = 60 - (now - calls_this_minute[0])
                logger.info(f"Rate limit - sleeping {sleep_time:.1f}s ({i}/{len(symbols)})")
                await asyncio.sleep(sleep_time)

            calls_this_minute.append(asyncio.get_event_loop().time())

            try:
                resp = await client.get(
                    f"{FINNHUB_BASE}/stock/short-interest",
                    params={"symbol": symbol, "token": api_key}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    # Finnhub returns {"data": [{"settlementDate": "2024-01-15", "shortInterest": 1234567, ...}]}
                    if data.get("data") and len(data["data"]) > 0:
                        latest = data["data"][0]  # Most recent
                        results[symbol] = {
                            "short_interest": latest.get("shortInterest", 0),
                            "avg_vol_30d": latest.get("avgDailyShareVolumeTraded", 0),
                            "days_to_cover": latest.get("daysToCover", 0),
                            "date": latest.get("settlementDate", "")
                        }
                elif resp.status_code == 429:
                    logger.warning(f"Rate limited at {symbol} - sleeping 60s")
                    await asyncio.sleep(60)
                    errors += 1
                else:
                    errors += 1

            except Exception as e:
                logger.debug(f"Error fetching {symbol}: {e}")
                errors += 1

            # Progress log every 500 symbols
            if (i + 1) % 500 == 0:
                logger.info(f"Progress: {i + 1}/{len(symbols)} ({len(results)} with data)")

    # Store results in database
    if results:
        async with db.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS short_interest (
                    symbol VARCHAR(10) PRIMARY KEY,
                    short_interest BIGINT,
                    avg_vol_30d BIGINT,
                    days_to_cover FLOAT,
                    settlement_date DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            for symbol, data in results.items():
                await conn.execute("""
                    INSERT INTO short_interest (symbol, short_interest, avg_vol_30d, days_to_cover, settlement_date, updated_at)
                    VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                    ON CONFLICT (symbol) DO UPDATE SET
                        short_interest = EXCLUDED.short_interest,
                        avg_vol_30d = EXCLUDED.avg_vol_30d,
                        days_to_cover = EXCLUDED.days_to_cover,
                        settlement_date = EXCLUDED.settlement_date,
                        updated_at = CURRENT_TIMESTAMP
                """, symbol, data["short_interest"], data["avg_vol_30d"],
                    data["days_to_cover"], data["date"] if data["date"] else None)

    logger.info(f"✅ Short interest complete: {len(results)} updated, {errors} errors")
    return {
        "success": True,
        "updated": len(results),
        "stocks_processed": len(symbols),
        "errors": errors
    }


@celery_app.task(name="tasks.fetch_short_interest", bind=True, soft_time_limit=3600, time_limit=3700)
def fetch_short_interest(self):
    """Daily Celery task to fetch short interest for all ACTIVE stocks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_fetch_short_interest_async())
    finally:
        loop.close()

