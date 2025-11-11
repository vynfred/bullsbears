#!/usr/bin/env python3
"""
Prime Database – FINAL v3.3 (November 11, 2025)
ONE-TIME: 90-day bootstrap via FMP Premium (7-week rolling batch)
Never run again after first success.
"""

import asyncio
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PRIME_DB")

async def main():
    """One-time Prime DB bootstrap – 90 days for all NASDAQ"""
    logger.info("PRIME DB BOOTSTRAP START – ONE-TIME ONLY")
    logger.info("=" * 70)

    try:
        # Import only what we need
        from app.services.fmp_data_ingestion import FMPIngestion
        from app.services.stock_classification_service import get_stock_classification_service

        # Initialize
        fmp = FMPIngestion()
        await fmp.initialize()
        stock_service = await get_stock_classification_service()

        # Safety check
        stats = await stock_service.get_tier_statistics()
        if stats.get("ALL", 0) > 1000:
            logger.warning(f"ALL tier already has {stats['ALL']:,} stocks")
            if input("Continue anyway? (y/N): ").strip().lower() != "y":
                logger.info("Bootstrap cancelled by user")
                return

        logger.info("Starting 90-day bootstrap – 7-week rolling batch")
        logger.info("This will take ~25 minutes – go grab coffee")

        start = datetime.now()
        await fmp.bootstrap_prime_db()
        duration = datetime.now() - start

        # Final verification
        final_stats = await stock_service.get_tier_statistics()
        count = final_stats.get("ALL", 0)

        logger.info("=" * 70)
        if count >= 3500:
            logger.info(f"PRIME DB SUCCESS – {count:,} NASDAQ stocks loaded")
            logger.info(f"Time taken: {duration}")
            logger.info("You are now READY for daily pipeline")
            logger.info("Next: : 3:00 AM ET → FMP daily delta")
        else:
            logger.error(f"PRIME FAILED – only {count:,} stocks")
            logger.error("Check FMP key, network, or run again")

    except KeyboardInterrupt:
        logger.info("Cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())