# backend/app/tasks/run_vision.py
"""
Vision Analysis Task - Fetches chart URLs from DB, sends images to Fireworks Vision API (Qwen3-VL)
"""
import asyncio
import logging
from datetime import datetime
from app.core.celery_app import celery_app
from app.services.cloud_agents import run_vision_analysis
from app.core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_vision")
def run_vision(prev_result=None):
    """Celery task to run vision analysis on chart images. Accepts prev_result for chain compatibility."""
    return asyncio.run(_run_vision())


async def _run_vision():
    """Fetch chart URLs and run vision analysis on images"""
    from app.services.activity_logger import log_activity, get_tier_counts
    start_time = datetime.now()

    db = await get_asyncpg_pool()

    # Get latest shortlist date
    async with db.acquire() as conn:
        latest = await conn.fetchrow("SELECT MAX(date) as latest_date FROM shortlist_candidates")

    if not latest or not latest['latest_date']:
        logger.info("No shortlist found")
        await log_activity("vision", "skipped", {"reason": "no_shortlist"})
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
        await log_activity("vision", "skipped", {"reason": "no_charts", "date": str(shortlist_date)})
        return {"status": "skipped", "reason": "no_charts"}

    # Log start
    await log_activity("vision", "started", {"charts_count": len(charts), "date": str(shortlist_date)})

    try:
        logger.info(f"Running vision analysis on {len(charts)} charts (date: {shortlist_date})")
        results = await run_vision_analysis([dict(c) for c in charts])

        success_count = sum(1 for r in results if any(r["vision_flags"].values()))
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Vision analysis complete: {success_count}/{len(results)} with flags")

        # Log completion
        tier_counts = await get_tier_counts()
        await log_activity("vision", "completed",
                          {"analyzed": len(results), "with_flags": success_count},
                          tier_counts=tier_counts, duration_seconds=elapsed)

        return {"status": "success", "analyzed": len(results), "with_flags": success_count}

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"Vision analysis failed: {e}")
        await log_activity("vision", "error", success=False,
                          error_message=str(e), duration_seconds=elapsed)
        raise