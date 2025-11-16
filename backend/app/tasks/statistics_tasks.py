#!/usr/bin/env python3
"""
BullsBears Statistics & Badges – FINAL v3.3 (November 12, 2025)
Real-time stats + badges — runs every 2–5 min — $0 cost
"""

import logging
from datetime import datetime
import asyncio

from ..core.celery import celery_app
from ..services.statistics_service import StatisticsService
from ..services.system_state import SystemState

logger = logging.getLogger(__name__)
stats_service = StatisticsService()  # singleton


@celery_app.task(name="tasks.update_statistics_cache")
def update_statistics_cache():
    """Every 5 min — full stats refresh"""
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping statistics cache update")
            return {"skipped": True, "reason": "system_off"}

        logger.info("Updating statistics cache")
        result = await stats_service.refresh_all_caches()
        logger.info("Stats cache updated")
        return result

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Stats cache failed: {e}")
        raise


@celery_app.task(name="tasks.update_badge_data_cache")
def update_badge_data_cache():
    """Every 2 min (market hours) — badge data for UI"""
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping badge data cache update")
            return {"skipped": True, "reason": "system_off"}

        logger.info("Updating badge data cache")
        result = await stats_service.refresh_badge_data()
        logger.info("Badge data updated")
        return result

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Badge cache failed: {e}")
        raise


@celery_app.task(name="tasks.validate_statistics_accuracy")
def validate_statistics_accuracy():
    """Every hour — data integrity"""
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping statistics validation")
            return {"skipped": True, "reason": "system_off"}

        logger.info("Validating statistics accuracy")
        result = await stats_service.validate_and_repair()
        logger.info(f"Validation: {result.get('status')}")
        return result

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise


@celery_app.task(name="tasks.generate_statistics_report")
def generate_statistics_report():
    """Daily — monitoring report"""
    async def _run():
        # Check if system is ON
        if not await SystemState.is_system_on():
            logger.info("⏸️ System is OFF - skipping statistics report")
            return {"skipped": True, "reason": "system_off"}

        logger.info("Generating daily statistics report")
        report = await stats_service.generate_daily_report()
        logger.info("Daily report generated")
        return report

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Report failed: {e}")
        raise