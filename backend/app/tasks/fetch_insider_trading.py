#!/usr/bin/env python3
"""
FMP Insider Trading Fetcher
Runs during pipeline after prescreen, before arbitrator
Uses FMP Premium API (300 calls/min)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_asyncpg_pool
from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v4"


async def _fetch_insider_for_shortlist_async():
    """
    Fetch insider trading data for today's shortlist candidates.
    Called after prescreen, before arbitrator.
    """
    if not await is_system_on():
        logger.info("⏸️ System is OFF - skipping insider fetch")
        return {"skipped": True, "reason": "system_off"}
    
    api_key = settings.FMP_API_KEY
    if not api_key:
        logger.warning("FMP_API_KEY not set - skipping insider trading")
        return {"success": False, "error": "no_api_key"}
    
    db = await get_asyncpg_pool()
    
    # Get shortlist symbols for latest date
    async with db.acquire() as conn:
        date_row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
        if not date_row or not date_row['latest_date']:
            logger.warning("No shortlist found")
            return {"success": False, "error": "no_shortlist"}
        
        shortlist_date = date_row['latest_date']
        rows = await conn.fetch("""
            SELECT symbol FROM shortlist_candidates WHERE date = $1
        """, shortlist_date)
        symbols = [r['symbol'] for r in rows]
    
    if not symbols:
        logger.warning("No shortlist symbols found")
        return {"success": False, "error": "no_symbols"}
    
    logger.info(f"📊 Fetching insider trading for {len(symbols)} shortlist stocks")
    
    import httpx
    results = {}
    errors = 0
    cutoff = datetime.now() - timedelta(days=90)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, symbol in enumerate(symbols):
            try:
                resp = await client.get(
                    f"{FMP_BASE}/insider-trading",
                    params={"symbol": symbol, "limit": 50, "apikey": api_key}
                )
                
                if resp.status_code == 200:
                    trades = resp.json()
                    
                    # Filter recent trades
                    recent = []
                    for t in trades:
                        try:
                            trade_date = datetime.strptime(t.get("transactionDate", ""), "%Y-%m-%d")
                            if trade_date >= cutoff:
                                recent.append(t)
                        except (ValueError, TypeError):
                            continue
                    
                    if recent:
                        # Calculate summary
                        buy_shares = sum(t.get("securitiesTransacted", 0) for t in recent 
                                        if t.get("transactionType") in ["P-Purchase", "A-Award"])
                        sell_shares = sum(t.get("securitiesTransacted", 0) for t in recent 
                                         if t.get("transactionType") in ["S-Sale", "S-Sale+OE"])
                        buy_count = sum(1 for t in recent if t.get("transactionType") in ["P-Purchase", "A-Award"])
                        sell_count = sum(1 for t in recent if t.get("transactionType") in ["S-Sale", "S-Sale+OE"])
                        
                        net_value = sum(
                            t.get("securitiesTransacted", 0) * t.get("price", 0) * 
                            (1 if t.get("transactionType") in ["P-Purchase", "A-Award"] else -1)
                            for t in recent
                        )
                        
                        results[symbol] = {
                            "has_activity": True,
                            "net_shares": buy_shares - sell_shares,
                            "net_value": round(net_value, 2),
                            "buy_count": buy_count,
                            "sell_count": sell_count,
                            "last_filing_date": recent[0].get("transactionDate") if recent else None,
                        }
                    else:
                        results[symbol] = {"has_activity": False, "net_shares": 0, "net_value": 0}
                else:
                    errors += 1
                    
            except Exception as e:
                logger.debug(f"Error fetching {symbol}: {e}")
                errors += 1
            
            # Small delay to stay under rate limit (300/min = 5/sec)
            await asyncio.sleep(0.25)
    
    # Update shortlist_candidates with insider data
    if results:
        async with db.acquire() as conn:
            for symbol, data in results.items():
                await conn.execute("""
                    UPDATE shortlist_candidates
                    SET insider_data = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE date = $2 AND symbol = $3
                """, json.dumps(data), shortlist_date, symbol)
    
    # Log summary of significant insider activity
    bullish_insiders = [s for s, d in results.items() if d.get("net_shares", 0) > 10000]
    bearish_insiders = [s for s, d in results.items() if d.get("net_shares", 0) < -10000]
    
    if bullish_insiders:
        logger.info(f"🟢 Insider BUYING: {', '.join(bullish_insiders[:5])}")
    if bearish_insiders:
        logger.info(f"🔴 Insider SELLING: {', '.join(bearish_insiders[:5])}")
    
    logger.info(f"✅ Insider trading complete: {len(results)} updated, {errors} errors")
    return {"success": True, "updated": len(results), "errors": errors}


@celery_app.task(name="tasks.fetch_insider_trading", bind=True, soft_time_limit=600, time_limit=660)
def fetch_insider_trading(self, prev_result=None):
    """Celery task to fetch insider trading for shortlist"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_fetch_insider_for_shortlist_async())
    finally:
        loop.close()

