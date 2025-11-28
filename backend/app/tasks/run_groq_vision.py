# backend/app/tasks/run_groq_vision.py
import asyncio
import logging
from app.core.celery_app import celery_app
from app.services.cloud_agents import run_vision_analysis
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_groq_vision")
def run_groq_vision():
    async def _run():
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            charts = await conn.fetch("""
                SELECT symbol, chart_base64 
                FROM shortlist_candidates 
                WHERE date = CURRENT_DATE AND chart_base64 IS NOT NULL
            """)

        if not charts:
            logger.info("No charts to analyze")
            return {"status": "skipped", "reason": "no_charts"}

        results = await run_vision_analysis([dict(c) for c in charts])
        logger.info(f"Vision analysis complete: {len(results)} charts")
        return {"status": "success", "analyzed": len(results)}

    return asyncio.run(_run())