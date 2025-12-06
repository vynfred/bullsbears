# backend/app/tasks/run_grok_social.py
import asyncio
import logging
from datetime import datetime
from app.core.celery_app import celery_app
from app.services.cloud_agents import run_social_analysis
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_grok_social")
def run_grok_social(prev_result=None):
    """Celery task to run social analysis. Accepts prev_result for chain compatibility."""
    async def _run():
        from app.services.activity_logger import log_activity, get_tier_counts
        start_time = datetime.now()

        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            symbols = await conn.fetch("""
                SELECT symbol FROM shortlist_candidates
                WHERE date = CURRENT_DATE
            """)

        if not symbols:
            logger.info("No symbols for social analysis")
            await log_activity("social", "skipped", {"reason": "no_symbols"})
            return {"status": "skipped"}

        # Log start
        await log_activity("social", "started", {"symbols_count": len(symbols)})

        try:
            results = await run_social_analysis([{"symbol": s["symbol"]} for s in symbols])
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Social analysis complete: {len(results)} symbols")

            # Log completion
            tier_counts = await get_tier_counts()
            await log_activity("social", "completed",
                              {"analyzed": len(results)},
                              tier_counts=tier_counts, duration_seconds=elapsed)

            return {"status": "success", "analyzed": len(results)}

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Social analysis failed: {e}")
            await log_activity("social", "error", success=False,
                              error_message=str(e), duration_seconds=elapsed)
            raise

    return asyncio.run(_run())