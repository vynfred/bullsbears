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
def run_arbitrator(prev_result=None):
    """
    Celery task - runs at 8:20 AM ET
    Selects 3–6 final picks using qwen2.5-72b-instruct on Fireworks
    Learner improves it every night via arbitrator_bias.json + prompt
    Accepts prev_result for chain compatibility.
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
            saved_count = 0
            updated_count = 0
            async with db.acquire() as conn:
                for pick in final_picks:
                    symbol = pick.get("symbol")
                    direction = pick.get("direction", "bullish")

                    # Check for existing pick within 30 days (avoid duplicates)
                    existing_pick = await conn.fetchrow("""
                        SELECT id, COALESCE(target_primary, primary_target) as target_primary,
                               target_medium, COALESCE(target_moonshot, moonshot_target) as target_moonshot,
                               direction
                        FROM picks
                        WHERE symbol = $1
                          AND created_at > NOW() - INTERVAL '30 days'
                          AND expires_at > NOW()
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, symbol)

                    candidate = await conn.fetchrow("""
                        SELECT * FROM shortlist_candidates
                        WHERE date = $1 AND symbol = $2
                    """, shortlist_date, symbol)

                    if not candidate:
                        logger.warning(f"Candidate data missing for {symbol}")
                        continue

                    # ═══════════════════════════════════════════════════════════════════
                    # v7 CATALYST DETECTION from social_data (headlines + short interest)
                    # ═══════════════════════════════════════════════════════════════════
                    social_data = json.loads(candidate['social_data'] or '{}') if candidate.get('social_data') else {}
                    headlines = social_data.get("headlines", [])

                    # Check headlines for news catalyst keywords
                    NEWS_KEYWORDS = ["fda", "merger", "acquisition", "partnership", "breakthrough",
                                     "approval", "deal", "contract", "guidance", "upgrade", "downgrade",
                                     "earnings", "revenue", "buyback", "dividend"]
                    has_news_catalyst = any(
                        keyword in headline.lower() for headline in headlines
                        for keyword in NEWS_KEYWORDS
                    )

                    # Get news sentiment from social score (-5 to +5 → -1 to +1)
                    news_sentiment = float(social_data.get("social_score", 0)) / 5.0  # Normalize

                    # Get short interest if available from prescreen data (stored in technical_snapshot)
                    tech_snapshot = json.loads(candidate['technical_snapshot'] or '{}') if candidate.get('technical_snapshot') else {}
                    short_interest_pct = float(tech_snapshot.get("short_interest_pct", 0))

                    # Calculate confluence-based targets (v7 - with catalyst data)
                    current_price = float(candidate['price_at_selection']) if candidate['price_at_selection'] else 0
                    conf_targets = await calculate_confluence_targets(
                        symbol=symbol,
                        current_price=current_price,
                        direction=direction,
                        db_pool=db,
                        has_news_catalyst=has_news_catalyst,
                        news_sentiment=news_sentiment,
                        short_interest_pct=short_interest_pct
                    )

                    if has_news_catalyst:
                        logger.info(f"📰 {symbol} has news catalyst: {headlines[:2]}")

                    # If stock was already picked in last 30 days, only update targets if needed
                    if existing_pick:
                        old_primary = float(existing_pick['target_primary']) if existing_pick['target_primary'] else 0
                        new_primary = conf_targets.target_primary

                        # Update targets if they've changed significantly (>2% difference)
                        if abs(new_primary - old_primary) / max(old_primary, 1) > 0.02:
                            await conn.execute("""
                                UPDATE picks
                                SET target_primary = $1,
                                    target_medium = $2,
                                    target_moonshot = $3,
                                    primary_target = $1,
                                    moonshot_target = $3,
                                    target_low = $1,
                                    target_high = COALESCE($3, $1 * 1.15),
                                    confluence_score = $4,
                                    confluence_methods = $5
                                WHERE id = $6
                            """,
                                conf_targets.target_primary,
                                conf_targets.target_medium,
                                conf_targets.target_moonshot,
                                conf_targets.confluence_score,
                                conf_targets.confluence_methods,
                                existing_pick['id']
                            )
                            logger.info(f"{symbol}: Updated targets (was ${old_primary:.2f}, now ${new_primary:.2f})")
                            updated_count += 1
                        else:
                            logger.info(f"{symbol}: Already picked within 30 days, targets unchanged - skipping")
                        continue  # Skip to next pick - don't create duplicate

                    # 3-TIER TARGETS: Primary always shown, Medium/Moonshot conditional
                    target_primary = conf_targets.target_primary
                    target_medium = conf_targets.target_medium  # None if confluence < 2
                    target_moonshot = conf_targets.target_moonshot  # None if confluence < 3 and no catalyst
                    stop_loss = conf_targets.stop_loss

                    logger.info(f"{symbol} ({direction}): price=${current_price:.2f}, "
                               f"primary=${target_primary:.2f}, medium={f'${target_medium:.2f}' if target_medium else 'N/A'}, "
                               f"moonshot={f'${target_moonshot:.2f}' if target_moonshot else 'N/A'}, "
                               f"confluence={conf_targets.confluence_score}/5 {conf_targets.confluence_methods}")

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
                            # 3-tier targets
                            "target_primary": conf_targets.target_primary,
                            "target_medium": conf_targets.target_medium,
                            "target_moonshot": conf_targets.target_moonshot,
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

                    # Insert final pick with 3-tier targets
                    pick_id = await conn.fetchval("""
                        INSERT INTO picks (
                            symbol, direction, confidence, reasoning,
                            target_low, target_high,
                            target_primary, target_medium, target_moonshot,
                            primary_target, moonshot_target,
                            confluence_score, confluence_methods, rsi_divergence, gann_alignment,
                            weekly_pivots,
                            pick_context, created_at, expires_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days'
                        ) RETURNING id
                    """,
                        symbol,
                        direction,
                        pick.get("confidence", 0.0),
                        pick.get("reasoning", ""),
                        target_primary,  # target_low for backward compat
                        target_moonshot if target_moonshot else target_primary * 1.15,  # target_high fallback
                        target_primary,
                        target_medium,
                        target_moonshot,
                        target_primary,  # Legacy primary_target
                        target_moonshot,  # Legacy moonshot_target
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

                    # Insert into pick_outcomes_detailed with 3-tier targets
                    await conn.execute("""
                        INSERT INTO pick_outcomes_detailed (
                            pick_id, symbol, direction,
                            price_when_picked,
                            target_primary, target_medium, target_moonshot,
                            outcome, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'active', CURRENT_TIMESTAMP)
                    """,
                        pick_id,
                        symbol,
                        direction,
                        current_price,
                        target_primary,
                        target_medium,
                        target_moonshot
                    )
                    saved_count += 1

            logger.info(f"Arbitrator complete: {saved_count} new picks, {updated_count} updated")
            return {
                "success": True,
                "picks_count": saved_count,
                "updated_count": updated_count,
                "symbols": [p["symbol"] for p in final_picks],
                "model": "qwen2.5-72b-instruct",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.exception("Arbitrator task failed")
            return {"success": False, "error": str(e)}

    return asyncio.run(_run())
