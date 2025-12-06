#!/usr/bin/env python3
"""
FMP Daily Delta Update
Runs at 3:00 AM ET
"""

import asyncio
import logging
from datetime import datetime
from app.services import get_fmp_ingestion
from app.services.system_state import is_system_on
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.fmp_delta_update")
def fmp_delta_update():
    async def _run():
        from app.services.activity_logger import log_activity, get_tier_counts
        start_time = datetime.now()

        # Check if system is ON
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping FMP delta update")
            await log_activity("fmp_update", "skipped", {"reason": "system_off"})
            return {"skipped": True, "reason": "system_off"}

        # Log start
        await log_activity("fmp_update", "started", {"source": "FMP API"})

        try:
            ingestion = await get_fmp_ingestion()
            result = await ingestion.daily_delta_update()

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("FMP daily delta complete")

            # Log completion with freshness info
            tier_counts = await get_tier_counts()
            await log_activity("fmp_update", "completed",
                              {"rows_updated": result.get("rows_updated", 0) if isinstance(result, dict) else 0},
                              tier_counts=tier_counts, duration_seconds=elapsed)

            return {"success": True}

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"FMP delta update failed: {e}")
            await log_activity("fmp_update", "error", success=False,
                              error_message=str(e), duration_seconds=elapsed)
            raise

    return asyncio.run(_run())
