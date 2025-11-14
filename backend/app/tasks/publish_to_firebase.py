#!/usr/bin/env python3
"""
Publish final picks to Firebase
Runs at 3:25 AM ET
"""

import asyncio
import logging
from app.services import push_picks_to_firebase
from app.core.database import get_database

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.publish_to_firebase")
def publish_to_firebase():
    async def _run():
        db = await get_database()
        picks = await db.fetch("SELECT * FROM final_picks WHERE date = CURRENT_DATE")
        
        picks_list = [dict(p) for p in picks]
        success = await push_picks_to_firebase(picks_list)
        
        logger.info(f"Published {len(picks_list)} picks → {'SUCCESS' if success else 'FAILED'}")
    
    asyncio.run(_run())