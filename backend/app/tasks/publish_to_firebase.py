#!/usr/bin/env python3
"""
Publish final picks to Firebase
Runs at 3:25 AM ET
"""

import asyncio
import logging
from app.services import push_picks_to_firebase
from app.core.database import get_asyncpg_pool
from app.services.system_state import SystemState
from app.core.celery import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.publish_to_firebase")
def publish_to_firebase():
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping Firebase publish")
            return {"skipped": True, "reason": "system_off"}

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            picks = await conn.fetch("SELECT * FROM final_picks WHERE date = CURRENT_DATE")

        picks_list = [dict(p) for p in picks]
        success = await push_picks_to_firebase(picks_list)

        logger.info(f"Published {len(picks_list)} picks → {'SUCCESS' if success else 'FAILED'}")
        return {"success": success, "picks_count": len(picks_list)}

    return asyncio.run(_run())