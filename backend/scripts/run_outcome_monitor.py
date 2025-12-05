#!/usr/bin/env python3
"""
BullsBears Outcome Monitor Runner
Triggered by Render Cron Job at 10 AM ET and 4:30 PM ET on weekdays

Checks all active picks for:
- Primary target hits
- Moonshot target hits  
- Expiration (30 days)

Updates pick_outcomes_detailed and picks.reasoning with outcome summaries.
"""

import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


async def main():
    """Run the outcome monitor with proper cleanup."""
    from app.services.system_state import is_system_on
    from app.tasks.monitor_pick_outcomes import _monitor_outcomes
    from app.core.database import close_asyncpg_pool
    from app.core.firebase import close_firebase

    logger.info("=" * 60)
    logger.info("OUTCOME MONITOR START")
    logger.info("=" * 60)

    try:
        # Check if system is ON
        if not await is_system_on():
            logger.info("⏸️ System is OFF - skipping outcome monitor")
            return {"skipped": True, "reason": "system_off"}

        result = await _monitor_outcomes()
        logger.info("=" * 60)
        logger.info(f"OUTCOME MONITOR COMPLETE: {result}")
        logger.info("=" * 60)
        return result
    except Exception as e:
        logger.error(f"❌ Outcome monitor failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # CRITICAL: Clean up async resources before event loop closes
        logger.info("🧹 Cleaning up async resources...")
        try:
            await close_asyncpg_pool()
        except Exception as e:
            logger.warning(f"asyncpg pool cleanup warning: {e}")
        try:
            await close_firebase()
        except Exception as e:
            logger.warning(f"Firebase cleanup warning: {e}")
        logger.info("✅ Cleanup complete")


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"Result: {result}")

