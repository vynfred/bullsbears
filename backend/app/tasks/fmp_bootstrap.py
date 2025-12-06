#!/usr/bin/env python3
"""
FMP Bootstrap Task
One-time 90-day database priming via Celery worker
"""

import asyncio
import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in Celery-safe way with fresh event loop and DB pool"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # Clean up the database pool before closing loop
        from app.core.database import close_asyncpg_pool
        try:
            loop.run_until_complete(close_asyncpg_pool())
        except:
            pass
        loop.close()


@celery_app.task(name="tasks.fmp_bootstrap", bind=True, max_retries=0, soft_time_limit=3600, time_limit=3700)
def fmp_bootstrap(self):
    """
    Full 90-day bootstrap - runs on Celery worker (no HTTP timeout)
    Takes ~25 minutes
    """
    async def _run():
        from datetime import datetime
        from app.services.fmp_data_ingestion import get_fmp_ingestion
        from app.services.activity_logger import log_activity, get_tier_counts

        start_time = datetime.now()
        await log_activity("fmp_bootstrap", "started", {"mode": "90-day full bootstrap"})

        logger.info("=" * 60)
        logger.info("FMP BOOTSTRAP TASK STARTED")
        logger.info("=" * 60)

        try:
            ingestion = await get_fmp_ingestion()
            await ingestion.bootstrap_prime_db()

            elapsed = (datetime.now() - start_time).total_seconds()
            tier_counts = await get_tier_counts()

            logger.info("=" * 60)
            logger.info(f"✅ BOOTSTRAP COMPLETE - {ingestion.daily_mb:.2f} MB")
            logger.info("=" * 60)

            await log_activity("fmp_bootstrap", "completed",
                             {"data_mb": round(ingestion.daily_mb, 2)},
                             tier_counts=tier_counts, duration_seconds=elapsed)

            return {
                "success": True,
                "data_mb": round(ingestion.daily_mb, 2)
            }

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ BOOTSTRAP FAILED: {e}")
            import traceback
            traceback.print_exc()
            await log_activity("fmp_bootstrap", "error", success=False,
                             error_message=str(e), duration_seconds=elapsed)
            return {
                "success": False,
                "error": str(e)
            }

    return run_async(_run())


@celery_app.task(name="tasks.fmp_catchup", bind=True, max_retries=0, soft_time_limit=600, time_limit=660)
def fmp_catchup(self):
    """
    7-day catchup for existing stocks
    Takes ~5 minutes
    """
    async def _run():
        from datetime import datetime
        from app.services.fmp_data_ingestion import get_fmp_ingestion
        from app.services.activity_logger import log_activity, get_tier_counts

        start_time = datetime.now()
        await log_activity("fmp_catchup", "started", {"mode": "7-day catchup"})

        logger.info("FMP 7-DAY CATCHUP TASK STARTED")

        try:
            ingestion = await get_fmp_ingestion()
            await ingestion.catchup_7days()

            elapsed = (datetime.now() - start_time).total_seconds()
            tier_counts = await get_tier_counts()

            logger.info(f"✅ CATCHUP COMPLETE - {ingestion.daily_mb:.2f} MB")

            await log_activity("fmp_catchup", "completed",
                             {"data_mb": round(ingestion.daily_mb, 2)},
                             tier_counts=tier_counts, duration_seconds=elapsed)

            return {
                "success": True,
                "data_mb": round(ingestion.daily_mb, 2)
            }

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ CATCHUP FAILED: {e}")
            await log_activity("fmp_catchup", "error", success=False,
                             error_message=str(e), duration_seconds=elapsed)
            return {
                "success": False,
                "error": str(e)
            }

    return run_async(_run())

