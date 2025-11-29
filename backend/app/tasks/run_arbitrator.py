#!/usr/bin/env python3
"""
Final Arbitrator Task – BullsBears v5 (November 2025)
Runs daily at 8:20 AM ET using qwen2.5-72b-instruct on Fireworks
No rotation. No fallback. Maximum win rate + nightly learner improvement.
"""

import asyncio
import logging
import json
from datetime import date
from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.cloud_agents.arbitrator_agent import get_final_picks
from app.core.database import get_asyncpg_pool
from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_arbitrator")
def run_arbitrator():
    """
    Celery task - runs at 8:20 AM ET
    Selects 3–6 final picks using qwen2.5-72b-instruct on Fireworks
    Learner improves it every night via arbitrator_bias.json + prompt
    """

    async def _run():
        # Kill switch — respects admin panel
        if not await is_system_on():
            logger.info("System is OFF – skipping arbitrator")
            return {"skipped": True, "reason": "system_off"}

        logger.info("Starting final arbitrator with qwen2.5-72b-instruct (Fireworks)")
        
        try:
            db = await get_asyncpg_pool()

            # Pull today's SHORT_LIST with all analysis
            async with db.acquire() as conn:
                shortlist = await conn.fetch("""
                    SELECT
                        symbol,
                        rank,
                        prescreen_score,
                        prescreen_reasoning,
                        price_at_selection,
                        technical_snapshot,
                        fundamental_snapshot,
                        vision_flags,
                        social_score,
                        social_data,
                        polymarket_prob
                    FROM shortlist_candidates
                    WHERE date::date = CURRENT_DATE
                    ORDER BY rank
                    LIMIT 75
                """)

            if not shortlist:
                logger.warning("No SHORT_LIST found for today")
                return {"success": False, "reason": "no_shortlist"}

            # Build phase_data for arbitrator
            phase_data = {
                "short_list": [dict(s) for s in shortlist],
                "vision_flags": {s["symbol"]: json.loads(s["vision_flags"]) for s in shortlist if s["vision_flags"]},
                "social_scores": {s["symbol"]: s["social_score"] for s in shortlist},
                "market_context": {},  # add VIX/SPY later if needed
            }

            logger.info(f"Arbitrator analyzing {len(shortlist)} stocks")

            # Single call to the best model
            result = await get_final_picks(phase_data)

            final_picks = result.get("final_picks", [])
            if not final_picks:
                logger.warning("Arbitrator returned no picks")
                return {"success": False, "reason": "no_picks_returned"}

            today = date.today()

            # Save picks + full context + create outcome tracking
            async with db.acquire() as conn:
                for pick in final_picks:
                    symbol = pick.get("symbol")
                    candidate = await conn.fetchrow("""
                        SELECT * FROM shortlist_candidates
                        WHERE date = $1 AND symbol = $2
                    """, today, symbol)

                    if not candidate:
                        logger.warning(f"Candidate data missing for {symbol}")
                        continue

                    pick_context = {
                        "technical": json.loads(candidate['technical_snapshot'] or '{}'),
                        "fundamental": json.loads(candidate['fundamental_snapshot'] or '{}'),
                        "ai_scores": {
                            "prescreen_score": candidate['prescreen_score'],
                            "prescreen_reasoning": candidate['prescreen_reasoning'],
                            "vision_flags": json.loads(candidate['vision_flags'] or '{}'),
                            "social_score": candidate['social_score'],
                            "social_data": json.loads(candidate['social_data'] or '{}'),
                            "polymarket_prob": candidate['polymarket_prob'],
                        },
                        "arbitrator": {
                            "model": "qwen2.5-72b-instruct",
                            "confidence": pick.get("confidence", 0.0),
                            "reasoning": pick.get("reasoning", "")
                        },
                        "market_context": phase_data.get("market_context", {})
                    }

                    # Insert final pick
                    pick_id = await conn.fetchval("""
                        INSERT INTO picks (
                            symbol, direction, confidence, reasoning,
                            target_low, target_low, target_high,
                            pick_context, created_at, expires_at
                            created_at, expires_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP + INTERVAL '30 days'
                        ) RETURNING id
                    """,
                        symbol,
                        pick.get("direction", "bullish"),
                        pick.get("confidence", 0.0),
                        pick.get("reasoning", ""),
                        pick.get("target_low"),
                        pick.get("target_high"),
                        json.dumps(pick_context)
                    )

                    # Mark as picked + create outcome tracker
                    await conn.execute("""
                        UPDATE shortlist_candidates
                        SET was_picked = TRUE,
                            picked_direction = $1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE date = $1 AND symbol = $2
                    """, pick.get("direction", "bullish"), today, symbol)

                    await conn.execute("""
                        INSERT INTO pick_outcomes_detailed (
                            pick_id, symbol, direction,
                            entry_price, target_low, target_high,
                            outcome, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, 'pending', CURRENT_TIMESTAMP)
                    """,
                        pick_id,
                        symbol,
                        pick.get("direction"),
                        candidate['price_at_selection'],
                        pick.get("target_low"),
                        pick.get("target_high")
                    )

            logger.info(f"Arbitrator complete: {len(final_picks)} picks saved")
            return {
                "success": True,
                "picks_count": len(final_picks),
                "symbols": [p["symbol"] for p in final_picks],
                "model": "qwen2.5-72b-instruct",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.exception("Arbitrator task failed")
            return {"success": False, "error": str(e)}

    return asyncio.run(_run())
