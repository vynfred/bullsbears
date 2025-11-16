#!/usr/bin/env python3
"""
Final Arbitrator Task - Selects 3-6 final picks
Runs at 8:20 AM ET using rotating cloud models (weekly cycle)
Models: DeepSeek-V3, Gemini 2.5 Pro, Grok-4, Claude Sonnet 4, GPT-5
"""

import asyncio
import logging
import json
from datetime import datetime, date
from app.core.celery import celery_app
from app.core.config import settings
from app.services.cloud_agents.arbitrator_agent import ArbitratorAgent
from app.core.database import get_asyncpg_pool
from app.services.system_state import SystemState

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_arbitrator")
def run_arbitrator():
    """
    Celery task - runs at 8:20 AM ET
    Makes final selection of 3-6 picks from 75 SHORT_LIST stocks
    Uses rotating cloud models (weekly cycle) to compare performance
    """
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping arbitrator")
            return {"skipped": True, "reason": "system_off"}

        # Get current arbitrator model based on weekly rotation
        current_model = settings.get_current_arbitrator()

        # Saturday = market closed, skip arbitrator
        if current_model is None:
            logger.info("📅 Saturday detected - market closed, skipping arbitrator")
            return {
                "status": "skipped",
                "reason": "Market closed on Saturday",
                "picks": []
            }

        week_num = datetime.now().isocalendar()[1]
        logger.info(f"⚖️ Starting final arbitrator task with {current_model} (Week {week_num})")
        start_time = datetime.now()

        try:
            db = await get_asyncpg_pool()

            # Get today's SHORT_LIST with all analysis data
            async with db.acquire() as conn:
                shortlist = await conn.fetch("""
                    SELECT
                        symbol,
                        rank,
                        prescreen_score,
                        vision_flags,
                        social_score,
                        social_headlines,
                        social_events,
                        polymarket_prob
                    FROM shortlist_candidates
                    WHERE date::date = CURRENT_DATE
                    ORDER BY rank
                    LIMIT 75
                """)

            if not shortlist:
                logger.warning("No SHORT_LIST found for today")
                return {"success": False, "reason": "no_shortlist"}

            # Prepare phase data for arbitrator
            phase_data = {
                "short_list": [dict(s) for s in shortlist],
                "vision_flags": {s["symbol"]: s["vision_flags"] for s in shortlist},
                "social_scores": {s["symbol"]: s["social_score"] for s in shortlist},
                "market_context": {}  # TODO: Add kill-switch data
            }

            logger.info(f"Arbitrator analyzing {len(shortlist)} stocks with {current_model}")

            # Run arbitrator with rotating model
            agent = ArbitratorAgent(cloud_model=current_model)
            await agent.initialize()
            result = await agent.make_final_selection(phase_data)
            
            # Store final picks in database with complete context
            final_picks = result.get("final_picks", [])
            today = date.today()

            async with db.acquire() as conn:
                for pick in final_picks:
                    symbol = pick.get("symbol")

                    # Get complete candidate data from shortlist_candidates
                    candidate = await conn.fetchrow("""
                        SELECT
                            prescreen_score, prescreen_reasoning,
                            price_at_selection,
                            technical_snapshot, fundamental_snapshot,
                            vision_flags, social_score, social_data, polymarket_prob
                        FROM shortlist_candidates
                        WHERE date = $1 AND symbol = $2
                    """, today, symbol)

                    if not candidate:
                        logger.warning(f"No candidate data found for {symbol}")
                        continue

                    # Build complete pick_context JSONB
                    pick_context = {
                        "technical": json.loads(candidate['technical_snapshot']) if candidate['technical_snapshot'] else {},
                        "fundamental": json.loads(candidate['fundamental_snapshot']) if candidate['fundamental_snapshot'] else {},
                        "ai_scores": {
                            "prescreen_score": float(candidate['prescreen_score']) if candidate['prescreen_score'] else 0.0,
                            "prescreen_reasoning": candidate['prescreen_reasoning'],
                            "vision_flags": json.loads(candidate['vision_flags']) if candidate['vision_flags'] else {},
                            "social_score": candidate['social_score'],
                            "social_data": json.loads(candidate['social_data']) if candidate['social_data'] else {},
                            "polymarket_prob": float(candidate['polymarket_prob']) if candidate['polymarket_prob'] else None
                        },
                        "arbitrator": {
                            "model": result.get("model_used", "qwen2.5:32b"),
                            "confidence": pick.get("confidence", 0.0),
                            "reasoning": pick.get("reasoning", "")
                        },
                        "market_context": phase_data.get("market_context", {})
                    }

                    # Insert into picks table with full context
                    pick_id = await conn.fetchval("""
                        INSERT INTO picks (
                            symbol, direction, confidence,
                            reasoning, target_low, target_high,
                            pick_context,
                            created_at, expires_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '3 days'
                        )
                        RETURNING id
                    """,
                        symbol,
                        pick.get("direction", "bullish"),
                        pick.get("confidence", 0.0),
                        pick.get("reasoning", ""),
                        pick.get("target_low"),
                        pick.get("target_high"),
                        json.dumps(pick_context)
                    )

                    # Mark candidate as picked
                    await conn.execute("""
                        UPDATE shortlist_candidates
                        SET was_picked = TRUE,
                            picked_direction = $1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE date = $2 AND symbol = $3
                    """, pick.get("direction", "bullish"), today, symbol)

                    # Create initial outcome tracking record
                    await conn.execute("""
                        INSERT INTO pick_outcomes_detailed (
                            pick_id, symbol, direction,
                            entry_price, target_low, target_high,
                            outcome, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, 'pending', CURRENT_TIMESTAMP)
                    """,
                        pick_id,
                        symbol,
                        pick.get("direction", "bullish"),
                        candidate['price_at_selection'],
                        pick.get("target_low"),
                        pick.get("target_high")
                    )

                    logger.info(f"✅ Stored pick {symbol} with full context (pick_id={pick_id})")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Arbitrator complete: {len(final_picks)} final picks in {elapsed:.1f}s")
            
            return {
                "success": True,
                "picks_count": len(final_picks),
                "picks": [p.get("symbol") for p in final_picks],
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Arbitrator task failed: {e}")
            raise
    
    return asyncio.run(_run())

