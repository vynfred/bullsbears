# backend/app/tasks/run_groq_vision.py
"""
Vision Analysis Task - Fetches chart URLs from DB, sends images to Groq Vision API
"""
import asyncio
import logging
from app.core.celery_app import celery_app
from app.services.cloud_agents import run_vision_analysis
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_groq_vision")
def run_groq_vision():
    """Celery task to run vision analysis on chart images"""
    return asyncio.run(_run_vision())


async def _run_vision():
    """Fetch chart URLs and run vision analysis on images"""
    db = await get_asyncpg_pool()

    # Get latest shortlist date
    async with db.acquire() as conn:
        latest = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")

    if not latest or not latest['latest_date']:
        logger.info("No shortlist found")
        return {"status": "skipped", "reason": "no_shortlist"}

    shortlist_date = latest['latest_date']

    # Get charts with URLs
    async with db.acquire() as conn:
        charts = await conn.fetch("""
            SELECT symbol, chart_url
            FROM shortlist_candidates
            WHERE date = $1 AND chart_url IS NOT NULL
            ORDER BY rank
        """, shortlist_date)

    if not charts:
        logger.info(f"No charts found for {shortlist_date}")
        return {"status": "skipped", "reason": "no_charts"}

    logger.info(f"Running vision analysis on {len(charts)} charts (date: {shortlist_date})")
    results = await run_vision_analysis([dict(c) for c in charts])

    success_count = sum(1 for r in results if any(r["vision_flags"].values()))
    logger.info(f"Vision analysis complete: {success_count}/{len(results)} with flags")

    return {"status": "success", "analyzed": len(results), "with_flags": success_count}