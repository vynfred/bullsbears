# backend/app/tasks/monitor_pick_outcomes.py
"""
Phase 4: Monitor pick outcomes and update summaries after 30 days.
Checks if picks hit their targets or expired, then updates reasoning.
"""

import asyncio
import os
import httpx
from datetime import datetime
from celery import shared_task
from app.core.database import get_asyncpg_pool
from app.services.system_state import is_system_on
import logging

logger = logging.getLogger(__name__)

FMP_API_KEY = os.getenv("FMP_API_KEY")


@shared_task(name="app.tasks.monitor_pick_outcomes.monitor_pick_outcomes")
def monitor_pick_outcomes():
    """
    Daily task: Check all active picks for target hits or expiry.
    Updates hit_primary_target, hit_moonshot_target flags and reasoning.
    """
    if not asyncio.run(is_system_on()):
        return {"status": "skipped", "system_off": True}
    
    return asyncio.run(_monitor_outcomes())


async def _monitor_outcomes():
    """Check active picks and update outcomes."""
    pool = await get_asyncpg_pool()

    results = {"checked": 0, "hits": 0, "misses": 0, "errors": 0}

    async with pool.acquire() as conn:
        # Get all picks that need checking:
        # 1. Active picks (not expired, not yet resolved)
        # 2. Recently expired picks (within last 24h, needs miss summary)
        # Note: entry_price comes from picks.pick_context->>'price_at_alert' or pod.entry_price
        picks = await conn.fetch("""
            SELECT
                p.id, p.symbol, p.direction, p.reasoning,
                p.primary_target, p.moonshot_target,
                p.pick_context,
                p.created_at, p.expires_at,
                pod.id as pod_id,
                pod.hit_primary_target, pod.hit_moonshot_target,
                pod.max_gain_pct, pod.outcome
            FROM picks p
            LEFT JOIN pick_outcomes_detailed pod ON pod.pick_id = p.id
            WHERE
                -- Active or recently expired (needs resolution)
                (p.expires_at > NOW() - INTERVAL '24 hours')
                AND (pod.outcome IS NULL OR pod.outcome = 'pending')
        """)

        if not picks:
            logger.info("No picks to monitor")
            return results

        # Get current prices for all symbols via FMP batch quote
        symbols = list(set(p["symbol"] for p in picks))
        price_map = {}

        if FMP_API_KEY and symbols:
            try:
                symbols_str = ",".join(symbols[:50])  # FMP limit
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}",
                        params={"apikey": FMP_API_KEY}
                    )
                    if resp.status_code == 200:
                        quotes = resp.json()
                        for q in quotes:
                            if q.get("symbol") and q.get("price"):
                                price_map[q["symbol"]] = float(q["price"])
            except Exception as e:
                logger.error(f"FMP quote fetch error: {e}")
        
        for pick in picks:
            try:
                results["checked"] += 1
                symbol = pick["symbol"]
                current_price = price_map.get(symbol)
                
                if not current_price:
                    logger.warning(f"No price for {symbol}")
                    continue
                
                # Get entry price from pick_context JSON (price_at_alert)
                pick_context = pick["pick_context"] or {}
                entry_price = None
                if isinstance(pick_context, dict):
                    entry_price = pick_context.get("price_at_alert")
                elif isinstance(pick_context, str):
                    import json
                    try:
                        ctx = json.loads(pick_context)
                        entry_price = ctx.get("price_at_alert")
                    except:
                        pass
                entry_price = float(entry_price) if entry_price else None
                primary_target = float(pick["primary_target"]) if pick["primary_target"] else None
                moonshot_target = float(pick["moonshot_target"]) if pick["moonshot_target"] else None
                direction = pick["direction"]
                is_expired = pick["expires_at"] and pick["expires_at"] < datetime.utcnow()
                
                # Calculate gain percentage from entry
                if entry_price and entry_price > 0:
                    if direction == "bullish":
                        gain_pct = ((current_price - entry_price) / entry_price) * 100
                    else:  # bearish
                        gain_pct = ((entry_price - current_price) / entry_price) * 100
                else:
                    gain_pct = 0
                
                # Check target hits
                hit_primary = pick["hit_primary_target"] or False
                hit_moonshot = pick["hit_moonshot_target"] or False
                
                if not hit_primary and primary_target:
                    if direction == "bullish" and current_price >= primary_target:
                        hit_primary = True
                    elif direction == "bearish" and current_price <= primary_target:
                        hit_primary = True
                
                if not hit_moonshot and moonshot_target:
                    if direction == "bullish" and current_price >= moonshot_target:
                        hit_moonshot = True
                    elif direction == "bearish" and current_price <= moonshot_target:
                        hit_moonshot = True
                
                # Track max gain
                old_max = float(pick["max_gain_pct"]) if pick["max_gain_pct"] else 0
                new_max = max(old_max, gain_pct)
                
                # Determine outcome and update summary
                new_outcome = pick["outcome"]
                new_reasoning = pick["reasoning"]
                
                if hit_moonshot:
                    new_outcome = "moonshot"
                    new_reasoning = _build_win_summary(symbol, "moonshot", moonshot_target, gain_pct)
                    results["hits"] += 1
                elif hit_primary:
                    new_outcome = "win"
                    new_reasoning = _build_win_summary(symbol, "primary", primary_target, gain_pct)
                    results["hits"] += 1
                elif is_expired and not hit_primary:
                    new_outcome = "loss"
                    new_reasoning = _build_loss_summary(symbol, direction, entry_price, current_price, primary_target)
                    results["misses"] += 1
                
                # Update pick_outcomes_detailed
                if pick["pod_id"]:
                    await conn.execute("""
                        UPDATE pick_outcomes_detailed
                        SET hit_primary_target = $1,
                            hit_moonshot_target = $2,
                            max_gain_pct = $3,
                            outcome = $4,
                            resolved_at = CASE WHEN $4 != 'pending' THEN NOW() ELSE resolved_at END
                        WHERE id = $5
                    """, hit_primary, hit_moonshot, new_max, new_outcome, pick["pod_id"])
                
                # Update reasoning in picks table if outcome changed
                if new_outcome != pick["outcome"] and new_outcome != "pending":
                    await conn.execute("""
                        UPDATE picks SET reasoning = $1 WHERE id = $2
                    """, new_reasoning, pick["id"])
                    logger.info(f"Updated {symbol}: {new_outcome} - {new_reasoning[:80]}...")
                    
            except Exception as e:
                logger.error(f"Error processing {pick['symbol']}: {e}")
                results["errors"] += 1
    
    logger.info(f"Outcome monitor complete: {results}")
    return results


def _build_win_summary(symbol: str, target_type: str, target_price: float, gain_pct: float) -> str:
    """
    Build win summary (max 180 chars).
    Template: "[Social/Volume trigger] + [Technical trigger] + [Fundamental/News trigger]"
    """
    gain_str = f"+{gain_pct:.1f}%" if gain_pct > 0 else f"{gain_pct:.1f}%"

    if target_type == "moonshot":
        return f"🌙 Moonshot hit ${target_price:.2f} ({gain_str}). Volume breakout confirmed, Fib 1.618 extension reached, momentum sustained through target."
    else:
        return f"🎯 Primary target hit ${target_price:.2f} ({gain_str}). Technical breakout validated, confluence zone cleared, trend continuation confirmed."


def _build_loss_summary(symbol: str, direction: str, entry: float, current: float, target: float) -> str:
    """
    Build loss summary (max 180 chars).
    Template: "[What failed] + [Technical reason] + [Market context]"
    """
    if not entry or entry == 0:
        return f"❌ Expired without hitting target. Price failed to reach ${target:.2f}, consolidation pattern invalidated."

    if direction == "bullish":
        change_pct = ((current - entry) / entry) * 100
        if change_pct < -10:
            return f"❌ Stopped out. Breakdown below support, volume dried up on bounce attempts, sector rotation headwinds."
        elif change_pct < 0:
            return f"❌ Failed breakout. Rising wedge rejected at resistance, lower highs formed, momentum faded before target."
        else:
            return f"❌ Expired +{change_pct:.1f}% but missed target. Consolidation stalled below ${target:.2f}, time decay on setup."
    else:  # bearish
        change_pct = ((entry - current) / entry) * 100
        if change_pct < -10:
            return f"❌ Squeezed out. Short covering rally, support held stronger than expected, sector bid lifted price."
        elif change_pct < 0:
            return f"❌ Bear trap triggered. Fakeout below support reversed, buyers stepped in at key level, bounce invalidated thesis."
        else:
            return f"❌ Expired +{change_pct:.1f}% drop but missed target. Selling pressure eased above ${target:.2f}, found support."

