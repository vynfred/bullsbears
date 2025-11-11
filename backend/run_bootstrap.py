#!/usr/bin/env python3
"""
BullsBears Database Bootstrap Script
Run this once to prime the database with 90 days of historical data
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.data_flow_manager import DataFlowManager
from app.core.database import get_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_database_migration():
    """Run the optimized database schema migration"""
    logger.info("🗄️ Running database schema migration...")
    
    try:
        db_pool = await get_database()
        
        # Read and execute the migration SQL
        migration_file = os.path.join(os.path.dirname(__file__), 
                                    'migrations', '003_optimized_production_schema.sql')
        
        if os.path.exists(migration_file):
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            async with db_pool.acquire() as conn:
                await conn.execute(migration_sql)
            
            logger.info("✅ Database schema migration completed")
        else:
            logger.warning("⚠️ Migration file not found, assuming schema exists")
            
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        raise


async def run_bootstrap():
    """Run the complete bootstrap process"""
    start_time = datetime.now()
    logger.info("🚀 STARTING BULLSBEARS DATABASE BOOTSTRAP")
    logger.info("=" * 60)
    
    try:
        # Step 1: Run database migration
        await run_database_migration()
        
        # Step 2: Initialize DataFlowManager
        logger.info("🔧 Initializing DataFlowManager...")
        manager = DataFlowManager()
        await manager.initialize()
        
        # Step 3: Bootstrap historical data
        logger.info("📊 Starting 90-day historical data bootstrap...")
        logger.info("This may take 15-30 minutes depending on API rate limits...")
        
        result = await manager.bootstrap_historical_data(days_back=90)
        
        # Step 4: Show results
        duration = datetime.now() - start_time
        logger.info("=" * 60)
        logger.info("✅ BOOTSTRAP COMPLETED SUCCESSFULLY!")
        logger.info(f"📈 Total symbols processed: {result.get('total_symbols', 0)}")
        logger.info(f"📊 Symbols with data: {result.get('updated_symbols', 0)}")
        logger.info(f"🎯 ACTIVE tier classified: {result.get('active_classified', 0)}")
        logger.info(f"⏱️ Total duration: {duration}")
        logger.info("=" * 60)
        
        # Step 5: Show pipeline status
        status = await manager.get_pipeline_status()
        logger.info("📋 PIPELINE STATUS:")
        logger.info(f"   Tier counts: {status.get('tier_counts', {})}")
        logger.info(f"   Latest data: {status.get('latest_data_timestamp', 'N/A')}")
        logger.info(f"   Kill switch: {'ACTIVE' if status.get('kill_switch_active') else 'INACTIVE'}")
        
        await manager.cleanup()
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Bootstrap failed: {e}")
        raise


async def test_pipeline_components():
    """Test individual pipeline components"""
    logger.info("🧪 TESTING PIPELINE COMPONENTS")
    logger.info("=" * 40)
    
    try:
        manager = DataFlowManager()
        await manager.initialize()
        
        # Test 1: Check database connection
        logger.info("Test 1: Database connection...")
        status = await manager.get_pipeline_status()
        logger.info(f"✅ Database connected: {status.get('status') == 'operational'}")
        
        # Test 2: Check FMP service
        logger.info("Test 2: FMP service...")
        from app.services.fmp_data_ingestion import get_fmp_service
        async with get_fmp_service() as fmp:
            nasdaq_symbols = await fmp.get_nasdaq_universe()
            logger.info(f"✅ FMP service: {len(nasdaq_symbols)} NASDAQ symbols available")
        
        # Test 3: Check chart generator
        logger.info("Test 3: Chart generator...")
        from app.services.chart_generator import get_chart_generator
        async with get_chart_generator() as chart_gen:
            logger.info("✅ Chart generator initialized")
        
        # Test 4: Check kill switch
        logger.info("Test 4: Kill switch service...")
        kill_switch_active = status.get('kill_switch_active', False)
        logger.info(f"✅ Kill switch: {'ACTIVE' if kill_switch_active else 'INACTIVE'}")
        
        await manager.cleanup()
        
        logger.info("=" * 40)
        logger.info("✅ ALL COMPONENTS TESTED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"❌ Component test failed: {e}")
        raise


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            await test_pipeline_components()
        elif command == 'bootstrap':
            await run_bootstrap()
        elif command == 'migration':
            await run_database_migration()
        else:
            print("Usage: python run_bootstrap.py [test|bootstrap|migration]")
            print("  test      - Test pipeline components")
            print("  bootstrap - Run full 90-day data bootstrap")
            print("  migration - Run database schema migration only")
    else:
        print("🚀 BullsBears Bootstrap Script")
        print("=" * 40)
        print("Choose an option:")
        print("1. Test components only")
        print("2. Run full bootstrap (90-day data)")
        print("3. Run database migration only")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            await test_pipeline_components()
        elif choice == '2':
            await run_bootstrap()
        elif choice == '3':
            await run_database_migration()
        else:
            print("Invalid choice")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bootstrap interrupted by user")
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        sys.exit(1)
