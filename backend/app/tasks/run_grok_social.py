# backend/app/tasks/run_grok_social.py
import asyncio
import logging
from app.core.celery_app import celery_app
from app.services.cloud_agents import run_social_analysis
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_grok_social")
def run_grok_social():
    async def _run():
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            symbols = await conn.fetch("""
                SELECT symbol FROM shortlist_candidates 
                WHERE date = CURRENT_DATE
            """)

        if not symbols:
            logger.info("No symbols for social analysis")
            return {"status": "skipped"}

        results = await run_social_analysis([{"symbol": s["symbol"]} for s in symbols])
        logger.info(f"Social analysis complete: {len(results)} symbols")
        return {"status": "success", "analyzed": len(results)}

    return asyncio.run(_run())