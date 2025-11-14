# app/tasks/run_learner.py
import asyncio
import logging
from app.core.celery import celery_app
from app.services.learner import run_nightly_learning
from app.services.system_state import SystemState

logger = logging.getLogger(__name__)

@celery_app.task
def trigger_learner():
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping nightly learning")
            return {"skipped": True, "reason": "system_off"}

        await run_nightly_learning()
        return {"success": True}

    return asyncio.run(_run())