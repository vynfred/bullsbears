#!/usr/bin/env python3
"""
FMP Bootstrap Task
One-time 90-day database priming via Celery worker
"""

import asyncio
import logging
from app.services.fmp_data_ingestion import get_fmp_ingestion
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.fmp_bootstrap", bind=True, max_retries=0, soft_time_limit=3600, time_limit=3700)
def fmp_bootstrap(self):
    """
    Full 90-day bootstrap - runs on Celery worker (no HTTP timeout)
    Takes ~25 minutes
    """
    async def _run():
        logger.info("=" * 60)
        logger.info("FMP BOOTSTRAP TASK STARTED")
        logger.info("=" * 60)
        
        try:
            ingestion = await get_fmp_ingestion()
            await ingestion.bootstrap_prime_db()
            
            logger.info("=" * 60)
            logger.info(f"✅ BOOTSTRAP COMPLETE - {ingestion.daily_mb:.2f} MB")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "data_mb": round(ingestion.daily_mb, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ BOOTSTRAP FAILED: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    return asyncio.run(_run())


@celery_app.task(name="tasks.fmp_catchup", bind=True, max_retries=0, soft_time_limit=600, time_limit=660)
def fmp_catchup(self):
    """
    7-day catchup for existing stocks
    Takes ~5 minutes
    """
    async def _run():
        logger.info("FMP 7-DAY CATCHUP TASK STARTED")
        
        try:
            ingestion = await get_fmp_ingestion()
            await ingestion.catchup_7days()
            
            logger.info(f"✅ CATCHUP COMPLETE - {ingestion.daily_mb:.2f} MB")
            
            return {
                "success": True,
                "data_mb": round(ingestion.daily_mb, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ CATCHUP FAILED: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    return asyncio.run(_run())

