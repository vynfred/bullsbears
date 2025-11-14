#!/usr/bin/env python3
"""
FMP Daily Delta Update
Runs at 3:00 AM ET
"""

import asyncio
import logging
from app.services import get_fmp_ingestion

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.fmp_delta_update")
def fmp_delta_update():
    async def _run():
        ingestion = await get_fmp_ingestion()
        await ingestion.daily_delta_update()
        logger.info("FMP daily delta complete")
    
    asyncio.run(_run())