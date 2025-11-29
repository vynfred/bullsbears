#!/usr/bin/env python3
"""
Build Active Symbols Task - NASDAQ ALL → ACTIVE Tier

"""

from celery import current_task
from ..core.celery_app import celery_app
from ..services.stock_filter_service import get_stock_filter_service
from ..services.system_state import is_system_on
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.build_active_symbols")
async def build_active_symbols(self):
    """Filter NASDAQ stocks to ACTIVE tier"""
    try:
        # Check if system is ON
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping ACTIVE tier filtering")
            return {"skipped": True, "reason": "system_off"}

        logger.info("🔍 Starting NASDAQ ALL → ACTIVE filtering task")

        filter_service = await get_stock_filter_service()
        active_stocks = await filter_service.filter_nasdaq_to_active()

        logger.info(f"✅ Task complete: {len(active_stocks)} ACTIVE stocks")

        return {
            "success": True,
            "active_count": len(active_stocks),
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"❌ build_active_symbols failed: {e}")
        raise