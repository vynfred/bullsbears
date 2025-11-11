#!/usr/bin/env python3
"""
Populate Stock Classifications Database
Uses DataFlowManager for proper data flow architecture
"""

import asyncio
import logging
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.data_flow_manager import DataFlowManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function to populate stock classifications using DataFlowManager"""
    logger.info("🚀 Starting Stock Classifications Population via DataFlowManager")
    logger.info("=" * 60)
    
    data_flow_manager = DataFlowManager()
    
    try:
        # Step 1: One-time initial setup (6-month historical data)
        logger.info("📊 Step 1: Initial data setup (6-month historical)")
        initial_result = await data_flow_manager.initial_data_setup()
        
        if initial_result["status"] == "already_initialized":
            logger.info(f"✅ ALL tier already initialized with {initial_result['count']} stocks")
        else:
            logger.info(f"✅ Initial setup complete: {initial_result['count']} stocks in ALL tier")
        
        # Step 2: Weekly prefilter to create ACTIVE tier
        logger.info("🔍 Step 2: Weekly prefilter (ALL → ACTIVE)")
        await data_flow_manager.run_weekly_prefilter()
        
        # Step 3: Generate tier statistics
        logger.info("📈 Step 3: Generating tier statistics")
        await generate_tier_statistics(data_flow_manager.db)
        
        logger.info("=" * 60)
        logger.info("✅ POPULATION COMPLETE!")
        logger.info("🔄 Ready for daily operations and 16+2 agent analysis")
        
    except Exception as e:
        logger.error(f"❌ Population failed: {e}")
        raise

async def generate_tier_statistics(db):
    """Generate and display tier statistics"""
    logger.info("Generating tier statistics...")
    
    try:
        stats = await db.fetch("""
            SELECT current_tier, COUNT(*) as count
            FROM stock_classifications
            GROUP BY current_tier
            ORDER BY 
                CASE current_tier
                    WHEN 'ALL' THEN 1
                    WHEN 'ACTIVE' THEN 2
                    WHEN 'QUALIFIED' THEN 3
                    WHEN 'SHORT_LIST' THEN 4
                    WHEN 'PICKS' THEN 5
                    ELSE 6
                END
        """)
        
        logger.info("📊 TIER STATISTICS:")
        logger.info("=" * 40)
        
        total_stocks = 0
        for stat in stats:
            tier = stat['current_tier']
            count = stat['count']
            total_stocks += count
            logger.info(f"{tier:>12}: {count:>6,} stocks")
        
        logger.info("=" * 40)
        logger.info(f"{'TOTAL':>12}: {total_stocks:>6,} stocks")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate statistics: {e}")

if __name__ == "__main__":
    asyncio.run(main())
