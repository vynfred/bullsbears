#!/usr/bin/env python3
"""
FMP Daily Delta Update
Runs at 3:00 AM ET
"""

import asyncio
import logging
from app.services import get_fmp_ingestion
from app.services.system_state import SystemState
from backend.app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.fmp_delta_update")
def fmp_delta_update():
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping FMP delta update")
            return {"skipped": True, "reason": "system_off"}

        ingestion = await get_fmp_ingestion()
        await ingestion.daily_delta_update()
        logger.info("FMP daily delta complete")
        return {"success": True}

    return asyncio.run(_run())