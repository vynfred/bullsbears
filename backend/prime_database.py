#!/usr/bin/env python3
"""
Prime Database Script - ONE-TIME INITIAL SETUP
Collects 1-week historical data for ALL NASDAQ stocks to prime the system
"""

import asyncio
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Prime the database with 1-week historical data"""
    try:
        logger.info("🚀 Starting DATABASE PRIMING - ONE-TIME INITIAL SETUP")
        logger.info("=" * 60)
        
        # Import services
        from app.services.data_flow_manager import DataFlowManager
        from app.services.stock_classification_service import StockClassificationService
        
        # Initialize services
        logger.info("Initializing services...")
        data_flow_manager = DataFlowManager()
        stock_service = StockClassificationService()
        
        await data_flow_manager.initialize()
        await stock_service.initialize()
        
        logger.info("✅ Services initialized")
        
        # Check if database is already primed
        tier_stats = await stock_service.get_tier_statistics()
        all_count = tier_stats.get('ALL', 0)
        if all_count > 0:
            logger.warning(f"⚠️ Database already contains {all_count} stocks in ALL tier")
            response = input("Continue with priming? This will add historical data. (y/N): ")
            if response.lower() != 'y':
                logger.info("❌ Priming cancelled by user")
                return
        
        # Run initial data setup (1-week historical collection)
        logger.info("🔄 Starting 1-week historical data collection...")
        logger.info("This is a ONE-TIME operation that primes the system")
        logger.info("Future updates will be weekly (ALL tier) + daily (ACTIVE tier)")
        
        await data_flow_manager.initial_data_setup()
        
        # Verify results
        final_stats = await stock_service.get_tier_statistics()
        final_all_count = final_stats.get('ALL', 0)
        logger.info("📊 PRIMING RESULTS:")
        logger.info("=" * 40)
        logger.info(f"ALL tier stocks: {final_all_count:,}")
        logger.info("=" * 40)
        
        if final_all_count > 0:
            logger.info("✅ DATABASE PRIMING COMPLETE!")
            logger.info("📅 System is now ready for:")
            logger.info("   - Weekly: ALL tier refresh + prefilter to ACTIVE")
            logger.info("   - Daily: ACTIVE tier updates + prescreen pipeline")
            logger.info("   - Daily: 16+2 agent analysis on SHORT_LIST")
        else:
            logger.error("❌ Priming failed - no stocks in ALL tier")
            
    except KeyboardInterrupt:
        logger.info("❌ Priming interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Priming failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
