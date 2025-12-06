#!/usr/bin/env python3
"""
Prescreen Task - ACTIVE → SHORT_LIST (~75 stocks)
Runs at 8:10 AM ET using Fireworks.ai qwen2.5-72b-instruct
"""

import asyncio
import logging
from datetime import datetime
from app.core.celery_app import celery_app
from app.services.cloud_agents.prescreen_agent import PrescreenAgent
from app.services.system_state import is_system_on

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_prescreen")
def run_prescreen(prev_result=None):
    """
    Celery task - runs at 8:10 AM ET via Render cron
    Filters ACTIVE tier (~1,700 stocks) → SHORT_LIST (exactly 75 stocks)
    Uses qwen2.5-72b-instruct on Fireworks.ai
    Accepts prev_result for chain compatibility.
    """

    # Run prescreen - single Fireworks API call
    async def _run():
        from app.services.activity_logger import log_activity, get_tier_counts

        # Check if system is ON
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping prescreen")
            await log_activity("prescreen", "skipped", {"reason": "system_off"})
            return {"skipped": True, "reason": "system_off"}

        logger.info("🔍 Starting ACTIVE → SHORT_LIST prescreen task")
        start_time = datetime.now()

        # Log start
        tier_counts = await get_tier_counts()
        await log_activity("prescreen", "started",
                          {"active_stocks": tier_counts.get("active", 0)},
                          tier_counts=tier_counts)

        try:
            # Initialize prescreen agent
            agent = PrescreenAgent()
            await agent.initialize()

            # Run prescreen - single Fireworks API call
            result = await agent.run_prescreen()

            elapsed = (datetime.now() - start_time).total_seconds()
            shortlist_count = result.get("shortlist_count", 0)
            logger.info(f"✅ Prescreen complete: {shortlist_count} stocks in {elapsed:.1f}s")

            # Log completion
            tier_counts = await get_tier_counts()
            await log_activity("prescreen", "completed",
                              {"shortlist_count": shortlist_count, "bullish": result.get("bullish", 0), "bearish": result.get("bearish", 0)},
                              tier_counts=tier_counts, duration_seconds=elapsed)

            return {
                "success": True,
                "shortlist_count": shortlist_count,
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Prescreen task failed: {e}")
            await log_activity("prescreen", "error", success=False,
                              error_message=str(e), duration_seconds=elapsed)
            raise

    return asyncio.run(_run())

