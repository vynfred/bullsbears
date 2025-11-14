#!/usr/bin/env python3
"""
Final Arbitrator Task - Selects 3-6 final picks
Runs at 8:20 AM ET using Qwen2.5:32b on RunPod
"""

import asyncio
import logging
from datetime import datetime
from app.core.celery import celery_app
from app.services.agents.arbitrator_agent import ArbitratorAgent
from app.core.database import get_asyncpg_pool
from app.services.system_state import SystemState

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_arbitrator")
def run_arbitrator():
    """
    Celery task - runs at 8:20 AM ET
    Makes final selection of 3-6 picks from 75 SHORT_LIST stocks
    Uses Qwen2.5:32b on RunPod serverless
    """
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping arbitrator")
            return {"skipped": True, "reason": "system_off"}
        
        logger.info("⚖️ Starting final arbitrator task")
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
            
            logger.info(f"Arbitrator analyzing {len(shortlist)} stocks")
            
            # Run arbitrator
            agent = ArbitratorAgent()
            await agent.initialize()
            result = await agent.make_final_selection(phase_data)
            
            # Store final picks in database
            final_picks = result.get("final_picks", [])
            async with db.acquire() as conn:
                for pick in final_picks:
                    await conn.execute("""
                        INSERT INTO final_picks (
                            date, symbol, confidence, target_low, target_medium, target_high,
                            reasoning, arbitrator_model, created_at
                        ) VALUES (
                            CURRENT_DATE, $1, $2, $3, $4, $5, $6, $7, NOW()
                        )
                        ON CONFLICT (date, symbol) DO UPDATE SET
                            confidence = EXCLUDED.confidence,
                            target_low = EXCLUDED.target_low,
                            target_medium = EXCLUDED.target_medium,
                            target_high = EXCLUDED.target_high,
                            reasoning = EXCLUDED.reasoning,
                            arbitrator_model = EXCLUDED.arbitrator_model,
                            created_at = NOW()
                    """,
                        pick.get("symbol"),
                        pick.get("confidence", 0.0),
                        pick.get("target_low"),
                        pick.get("target_medium"),
                        pick.get("target_high"),
                        pick.get("reasoning", ""),
                        result.get("model_used", "qwen2.5:32b")
                    )
            
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

