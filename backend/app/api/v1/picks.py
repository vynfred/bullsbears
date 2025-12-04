# backend/app/api/v1/picks.py
"""
Picks API - Serves live AI picks to frontend
Auto-checks target hits on every price fetch (replaces scheduled cron)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/picks", tags=["picks"])
logger = logging.getLogger(__name__)


async def _check_and_update_target_hits(conn, rows: List, current_prices: Dict[str, float]):
    """
    Check if any picks hit their targets based on fresh FMP prices.
    Updates database immediately when targets are hit.

    For BULLISH picks: price >= primary_target = win
    For BEARISH picks: price <= primary_target = win (price dropped to target)
    """
    updates = []

    for row in rows:
        pick_id = row["id"]
        symbol = row["symbol"]
        direction = row["direction"]
        current_price = current_prices.get(symbol)

        if not current_price:
            continue

        # Skip if already marked as hit
        if row.get("hit_primary_target") or row.get("hit_moonshot_target"):
            continue

        primary_target = float(row["primary_target"]) if row.get("primary_target") else None
        moonshot_target = float(row["moonshot_target"]) if row.get("moonshot_target") else None

        hit_primary = False
        hit_moonshot = False

        if direction == "bullish":
            # Bullish: price needs to GO UP to hit target
            if primary_target and current_price >= primary_target:
                hit_primary = True
            if moonshot_target and current_price >= moonshot_target:
                hit_moonshot = True
        else:
            # Bearish: price needs to GO DOWN to hit target
            if primary_target and current_price <= primary_target:
                hit_primary = True
            if moonshot_target and current_price <= moonshot_target:
                hit_moonshot = True

        if hit_primary or hit_moonshot:
            updates.append({
                "pick_id": pick_id,
                "symbol": symbol,
                "direction": direction,
                "hit_primary": hit_primary,
                "hit_moonshot": hit_moonshot,
                "price_at_hit": current_price
            })

    # Log pending updates
    if updates:
        logger.info(f"🎯 Found {len(updates)} target hits to update: {[u['symbol'] for u in updates]}")

    # Batch update hits in database
    for upd in updates:
        try:
            # First check if row exists
            existing = await conn.fetchrow(
                "SELECT id FROM pick_outcomes_detailed WHERE pick_id = $1",
                upd["pick_id"]
            )

            if existing:
                # Update existing row
                await conn.execute("""
                    UPDATE pick_outcomes_detailed
                    SET hit_primary_target = $2,
                        hit_moonshot_target = $3,
                        price_at_hit = $4,
                        hit_at = CURRENT_TIMESTAMP
                    WHERE pick_id = $1
                """, upd["pick_id"], upd["hit_primary"], upd["hit_moonshot"], upd["price_at_hit"])
            else:
                # Insert new row - include required symbol and direction columns
                await conn.execute("""
                    INSERT INTO pick_outcomes_detailed (pick_id, symbol, direction, hit_primary_target, hit_moonshot_target, price_at_hit, hit_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                """, upd["pick_id"], upd["symbol"], upd["direction"], upd["hit_primary"], upd["hit_moonshot"], upd["price_at_hit"])

            logger.info(f"🎯 TARGET HIT: {upd['symbol']} (pick_id={upd['pick_id']}) - primary={upd['hit_primary']}, moonshot={upd['hit_moonshot']} @ ${upd['price_at_hit']:.2f}")
        except Exception as e:
            logger.error(f"Failed to update target hit for {upd['symbol']}: {e}")


@router.get("/live")
async def get_live_picks(
    sentiment: Optional[str] = Query(None, description="Filter by bullish or bearish"),
    period: Optional[str] = Query("today", description="Filter: today, 7d, all, active"),
    outcome: Optional[str] = Query(None, description="Filter: wins, losses"),
    limit: int = Query(25, ge=1, le=100),
    min_confidence: int = Query(0, ge=0, le=100)
):
    """
    Get live AI picks from database with real-time prices from FMP.

    Filters:
    - period: today (default), 7d (last 7 days), all (all time), active (within 30-day window)
    - sentiment: bullish, bearish
    - outcome: wins (hit target), losses (expired without hit)
    """
    try:
        from app.core.database import get_asyncpg_pool
        from app.core.config import settings
        import httpx

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Check if picks table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'picks'
                )
            """)

            if not exists:
                logger.warning("Picks table doesn't exist yet")
                return []

            # Build dynamic query - only select columns that exist
            # Note: pick_outcomes_detailed may not have all columns yet
            query = """
                SELECT
                    p.id, p.symbol, p.direction, p.confidence, p.reasoning,
                    p.target_low, p.target_high, p.pick_context, p.pretty_chart_url,
                    p.primary_target, p.moonshot_target,
                    p.confluence_score,
                    p.created_at, p.expires_at,
                    pod.hit_primary_target, pod.hit_moonshot_target
                FROM picks p
                LEFT JOIN pick_outcomes_detailed pod ON pod.pick_id = p.id
                WHERE p.confidence >= $1
            """
            params = [min_confidence / 100.0]
            param_idx = 2

            # Period filter
            if period == "today":
                query += f" AND p.created_at::date = CURRENT_DATE"
            elif period == "7d":
                query += f" AND p.created_at >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == "active":
                query += f" AND p.expires_at > CURRENT_TIMESTAMP"
            # "all" has no date filter

            # Direction/sentiment filter
            if sentiment:
                query += f" AND p.direction = ${param_idx}"
                params.append(sentiment)
                param_idx += 1

            # Outcome filter
            if outcome == "wins":
                query += f" AND (pod.hit_primary_target = TRUE OR pod.hit_moonshot_target = TRUE)"
            elif outcome == "losses":
                query += f" AND p.expires_at < CURRENT_TIMESTAMP AND (pod.hit_primary_target IS NULL OR pod.hit_primary_target = FALSE)"

            query += f" ORDER BY p.created_at DESC LIMIT ${param_idx}"
            params.append(limit)

            rows = await conn.fetch(query, *params)

            # Get chart URLs from shortlist_candidates
            symbol_list = [row["symbol"] for row in rows]
            chart_data = {}
            price_at_pick = {}

            if symbol_list:
                # Get latest shortlist date
                date_row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
                if date_row and date_row['latest_date']:
                    shortlist_date = date_row['latest_date']

                    # Get chart URLs and prices for these symbols
                    chart_rows = await conn.fetch("""
                        SELECT symbol, chart_url, price_at_selection
                        FROM shortlist_candidates
                        WHERE date = $1 AND symbol = ANY($2)
                    """, shortlist_date, symbol_list)

                    for cr in chart_rows:
                        chart_data[cr["symbol"]] = cr["chart_url"]
                        price_at_pick[cr["symbol"]] = float(cr["price_at_selection"]) if cr["price_at_selection"] else None

            # Fetch real-time prices from FMP (batch quote)
            current_prices = {}
            if symbol_list and settings.FMP_API_KEY:
                try:
                    symbols_str = ",".join(symbol_list)
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(
                            f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}",
                            params={"apikey": settings.FMP_API_KEY}
                        )
                        if resp.status_code == 200:
                            quotes = resp.json()
                            for q in quotes:
                                current_prices[q["symbol"]] = float(q.get("price", 0))
                except Exception as e:
                    logger.warning(f"Failed to fetch FMP quotes: {e}")

            # ═══════════════════════════════════════════════════════════════════
            # AUTO-CHECK TARGET HITS on every price fetch (replaces cron job)
            # ═══════════════════════════════════════════════════════════════════
            if current_prices:
                await _check_and_update_target_hits(conn, rows, current_prices)

            # Transform to frontend format
            picks = []
            for row in rows:
                symbol = row["symbol"]
                # confidence is already stored as a decimal (0.85) or percentage (85) - check value
                conf_value = float(row["confidence"]) if row["confidence"] else 0
                # If confidence > 1, it's already a percentage; otherwise multiply by 100
                confidence_pct = conf_value if conf_value > 1 else conf_value * 100

                entry_price = price_at_pick.get(symbol)
                current_price = current_prices.get(symbol) or entry_price

                # Calculate % change since picked
                change_pct = None
                if entry_price and current_price and entry_price > 0:
                    change_pct = ((current_price - entry_price) / entry_price) * 100

                # Determine outcome status for styling
                hit_primary = row.get("hit_primary_target") or False
                hit_moonshot = row.get("hit_moonshot_target") or False
                is_expired = row["expires_at"] and row["expires_at"] < datetime.utcnow()

                if hit_moonshot:
                    outcome_status = "moonshot"  # Gold with sparkles
                elif hit_primary:
                    outcome_status = "win"  # Gold
                elif is_expired and not hit_primary:
                    outcome_status = "loss"  # Purple
                else:
                    outcome_status = "active"  # Green/Red based on direction

                pick_data = {
                    "id": row["id"],
                    "symbol": symbol,
                    "direction": row["direction"],
                    "confidence": confidence_pct,
                    "reasoning": row["reasoning"],
                    "target_low": float(row["target_low"]) if row["target_low"] else None,
                    "target_high": float(row["target_high"]) if row["target_high"] else None,
                    # Confluence v5 fields
                    "primary_target": float(row["primary_target"]) if row.get("primary_target") else None,
                    "moonshot_target": float(row["moonshot_target"]) if row.get("moonshot_target") else None,
                    "confluence_score": int(row["confluence_score"]) if row.get("confluence_score") else 0,
                    "rsi_divergence": bool(row.get("rsi_divergence")),
                    "gann_alignment": bool(row.get("gann_alignment")),
                    "weekly_pivots": row.get("weekly_pivots"),
                    # Outcome tracking
                    "hit_primary_target": hit_primary,
                    "hit_moonshot_target": hit_moonshot,
                    "outcome_status": outcome_status,
                    # Price/chart data
                    "context": row["pick_context"],
                    "chart_url": chart_data.get(symbol),
                    "pretty_chart_url": row.get("pretty_chart_url"),
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "change_pct": round(change_pct, 2) if change_pct is not None else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                }

                picks.append(pick_data)

            return picks

    except Exception as e:
        import traceback
        logger.error(f"Error fetching picks: {e}\n{traceback.format_exc()}")
        # Return error info for debugging - frontend should handle gracefully
        raise HTTPException(status_code=500, detail=f"Error fetching picks: {str(e)}")


@router.get("/debug")
async def debug_picks():
    """Debug endpoint to see raw query results"""
    try:
        from app.core.database import get_asyncpg_pool

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Simple query - no joins
            rows = await conn.fetch("""
                SELECT id, symbol, direction, confidence, created_at
                FROM picks
                ORDER BY created_at DESC
                LIMIT 5
            """)

            return {
                "count": len(rows),
                "picks": [dict(r) for r in rows],
                "debug": "Raw query without joins"
            }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/today")
async def get_todays_picks():
    """Get today's picks summary for dashboard badge"""
    try:
        from app.core.database import get_asyncpg_pool
        
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Check if picks table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'picks'
                )
            """)
            
            if not exists:
                return {"bullish": 0, "bearish": 0, "total": 0, "last_updated": None}
            
            today = datetime.utcnow().date()
            
            result = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE direction = 'bullish') as bullish,
                    COUNT(*) FILTER (WHERE direction = 'bearish') as bearish,
                    COUNT(*) as total,
                    MAX(created_at) as last_updated
                FROM picks
                WHERE DATE(created_at) = $1
            """, today)
            
            return {
                "bullish": result["bullish"] or 0,
                "bearish": result["bearish"] or 0,
                "total": result["total"] or 0,
                "last_updated": result["last_updated"].isoformat() if result["last_updated"] else None
            }
            
    except Exception as e:
        logger.error(f"Error fetching today's picks: {e}")
        return {"bullish": 0, "bearish": 0, "total": 0, "last_updated": None}


@router.post("/check-targets")
async def manual_check_targets():
    """Manually check and update target hits for all picks"""
    try:
        from app.core.database import get_asyncpg_pool
        from app.core.config import settings
        import httpx

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            # Get all active picks with their targets
            rows = await conn.fetch("""
                SELECT p.id, p.symbol, p.direction, p.primary_target, p.moonshot_target,
                       pod.hit_primary_target, pod.hit_moonshot_target
                FROM picks p
                LEFT JOIN pick_outcomes_detailed pod ON pod.pick_id = p.id
                WHERE p.expires_at > NOW()
            """)

            if not rows:
                return {"message": "No active picks found", "checked": 0, "updated": 0}

            symbol_list = list(set(r["symbol"] for r in rows))

            # Fetch current prices
            current_prices = {}
            symbols_str = ",".join(symbol_list)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}",
                    params={"apikey": settings.FMP_API_KEY}
                )
                if resp.status_code == 200:
                    for q in resp.json():
                        current_prices[q["symbol"]] = float(q.get("price", 0))

            # Check targets
            updates = []
            for row in rows:
                symbol = row["symbol"]
                direction = row["direction"]
                current_price = current_prices.get(symbol, 0)
                primary_target = float(row["primary_target"]) if row["primary_target"] else None
                moonshot_target = float(row["moonshot_target"]) if row["moonshot_target"] else None

                # Skip already hit
                if row["hit_primary_target"] or row["hit_moonshot_target"]:
                    continue

                hit_primary = False
                hit_moonshot = False

                if direction == "bullish":
                    if primary_target and current_price >= primary_target:
                        hit_primary = True
                    if moonshot_target and current_price >= moonshot_target:
                        hit_moonshot = True
                else:
                    if primary_target and current_price <= primary_target:
                        hit_primary = True
                    if moonshot_target and current_price <= moonshot_target:
                        hit_moonshot = True

                if hit_primary or hit_moonshot:
                    updates.append({
                        "pick_id": row["id"],
                        "symbol": symbol,
                        "direction": direction,
                        "current_price": current_price,
                        "primary_target": primary_target,
                        "hit_primary": hit_primary,
                        "hit_moonshot": hit_moonshot
                    })

            # Apply updates
            updated_count = 0
            for upd in updates:
                existing = await conn.fetchrow(
                    "SELECT id FROM pick_outcomes_detailed WHERE pick_id = $1",
                    upd["pick_id"]
                )

                if existing:
                    await conn.execute("""
                        UPDATE pick_outcomes_detailed
                        SET hit_primary_target = $2, hit_moonshot_target = $3, price_at_hit = $4, hit_at = NOW()
                        WHERE pick_id = $1
                    """, upd["pick_id"], upd["hit_primary"], upd["hit_moonshot"], upd["current_price"])
                else:
                    await conn.execute("""
                        INSERT INTO pick_outcomes_detailed (pick_id, symbol, direction, hit_primary_target, hit_moonshot_target, price_at_hit, hit_at)
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """, upd["pick_id"], upd["symbol"], upd["direction"], upd["hit_primary"], upd["hit_moonshot"], upd["current_price"])
                updated_count += 1

            return {
                "checked": len(rows),
                "prices_fetched": len(current_prices),
                "updated": updated_count,
                "updates": updates
            }

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
