#!/usr/bin/env python3
"""
Final Arbitrator Task – BullsBears v5 (November 2025)
Runs daily at 8:20 AM ET using qwen2.5-72b-instruct on Fireworks
No rotation. No fallback. Maximum win rate + nightly learner improvement.
"""

import asyncio
import logging
import json
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.cloud_agents.arbitrator_agent import get_final_picks
from app.core.database import get_asyncpg_pool
from app.services.system_state import is_system_on
from app.services.fib_calculator import calculate_confluence_targets

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

            # Pull latest SHORT_LIST with all analysis (may not be today)
            async with db.acquire() as conn:
                # Get latest shortlist date
                date_row = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")
                if not date_row or not date_row['latest_date']:
                    logger.warning("No shortlist found in database")
                    return {"success": False, "reason": "no_shortlist"}
                shortlist_date = date_row['latest_date']
                logger.info(f"Using shortlist date: {shortlist_date}")

                shortlist = await conn.fetch("""
                    SELECT
                        symbol,
                        rank,
                        direction,
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
                    WHERE date = $1
                    ORDER BY rank
                    LIMIT 75
                """, shortlist_date)

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

            # Save picks + full context + create outcome tracking
            async with db.acquire() as conn:
                for pick in final_picks:
                    symbol = pick.get("symbol")
                    direction = pick.get("direction", "bullish")

                    candidate = await conn.fetchrow("""
                        SELECT * FROM shortlist_candidates
                        WHERE date = $1 AND symbol = $2
                    """, shortlist_date, symbol)

                    if not candidate:
                        logger.warning(f"Candidate data missing for {symbol}")
                        continue

                    # Calculate confluence-based targets (v5 - deterministic math)
                    current_price = float(candidate['price_at_selection']) if candidate['price_at_selection'] else 0
                    conf_targets = await calculate_confluence_targets(
                        symbol=symbol,
                        current_price=current_price,
                        direction=direction,
                        db_pool=db
                    )

                    # Primary target always shown, moonshot conditional on confluence score
                    primary_target = conf_targets.primary_target
                    moonshot_target = conf_targets.moonshot_target  # None if conditions not met
                    stop_loss = conf_targets.stop_loss

                    logger.info(f"{symbol} ({direction}): price=${current_price:.2f}, "
                               f"primary=${primary_target:.2f}, moonshot={f'${moonshot_target:.2f}' if moonshot_target else 'N/A'}, "
                               f"confluence={conf_targets.confluence_score}/4 {conf_targets.confluence_methods}")

                    # Serialize weekly pivots for charting
                    weekly_pivots_dict = None
                    if conf_targets.weekly_pivots:
                        weekly_pivots_dict = {
                            "pivot": conf_targets.weekly_pivots.pivot,
                            "r1": conf_targets.weekly_pivots.r1,
                            "r2": conf_targets.weekly_pivots.r2,
                            "s1": conf_targets.weekly_pivots.s1,
                            "s2": conf_targets.weekly_pivots.s2
                        }

                    pick_context = {
                        "technical": json.loads(candidate['technical_snapshot'] or '{}'),
                        "fundamental": json.loads(candidate['fundamental_snapshot'] or '{}'),
                        "ai_scores": {
                            "prescreen_score": float(candidate['prescreen_score']) if candidate['prescreen_score'] else 0.0,
                            "prescreen_reasoning": candidate['prescreen_reasoning'],
                            "vision_flags": json.loads(candidate['vision_flags'] or '{}'),
                            "social_score": float(candidate['social_score']) if candidate['social_score'] else 0.0,
                            "social_data": json.loads(candidate['social_data'] or '{}'),
                            "polymarket_prob": float(candidate['polymarket_prob']) if candidate['polymarket_prob'] else None,
                        },
                        "arbitrator": {
                            "model": "qwen2.5-72b-instruct",
                            "confidence": pick.get("confidence", 0.0),
                            "reasoning": pick.get("reasoning", "")
                        },
                        "confluence_analysis": {
                            "swing_low": conf_targets.swing_low,
                            "swing_high": conf_targets.swing_high,
                            "primary_target": conf_targets.primary_target,
                            "moonshot_target": conf_targets.moonshot_target,
                            "stop_loss": conf_targets.stop_loss,
                            "confluence_score": conf_targets.confluence_score,
                            "confluence_methods": conf_targets.confluence_methods,
                            "gann_alignment": conf_targets.gann_alignment,
                            "rsi_divergence": conf_targets.rsi_divergence.detected if conf_targets.rsi_divergence else False,
                            "rsi_divergence_type": conf_targets.rsi_divergence.divergence_type if conf_targets.rsi_divergence else None,
                            "atr_pct": conf_targets.atr_pct,
                            "valid_setup": conf_targets.valid,
                            "invalidation_reason": conf_targets.invalidation_reason
                        },
                        "market_context": phase_data.get("market_context", {})
                    }

                    # Insert final pick with confluence data
                    pick_id = await conn.fetchval("""
                        INSERT INTO picks (
                            symbol, direction, confidence, reasoning,
                            target_low, target_high,
                            primary_target, moonshot_target,
                            confluence_score, confluence_methods, rsi_divergence, gann_alignment,
                            weekly_pivots,
                            pick_context, created_at, expires_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days'
                        ) RETURNING id
                    """,
                        symbol,
                        direction,
                        pick.get("confidence", 0.0),
                        pick.get("reasoning", ""),
                        primary_target,  # Keep target_low for backward compat
                        moonshot_target if moonshot_target else primary_target * 1.15,  # target_high fallback
                        primary_target,
                        moonshot_target,
                        conf_targets.confluence_score,
                        conf_targets.confluence_methods,
                        conf_targets.rsi_divergence.detected if conf_targets.rsi_divergence else False,
                        conf_targets.gann_alignment,
                        json.dumps(weekly_pivots_dict) if weekly_pivots_dict else None,
                        json.dumps(pick_context)
                    )

                    # Mark as picked + create outcome tracker
                    await conn.execute("""
                        UPDATE shortlist_candidates
                        SET was_picked = TRUE,
                            picked_direction = $1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE date = $2 AND symbol = $3
                    """, direction, shortlist_date, symbol)

                    await conn.execute("""
                        INSERT INTO pick_outcomes_detailed (
                            pick_id, symbol, direction,
                            entry_price, target_low, target_high,
                            primary_target, moonshot_target, confluence_score,
                            outcome, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending', CURRENT_TIMESTAMP)
                    """,
                        pick_id,
                        symbol,
                        direction,
                        current_price,
                        primary_target,  # Keep target_low for backward compat
                        moonshot_target if moonshot_target else primary_target * 1.15,
                        primary_target,
                        moonshot_target,
                        conf_targets.confluence_score
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
