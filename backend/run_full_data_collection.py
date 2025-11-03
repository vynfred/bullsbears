#!/usr/bin/env python3
"""
Full-Scale NASDAQ Data Collection Script
Downloads 6 months of historical data for all 6,961 NASDAQ stocks using Databento API.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Fallback: Set API key directly if not loaded
if not os.getenv('DATABENTO_API_KEY'):
    os.environ['DATABENTO_API_KEY'] = 'db-fSF3pUC5SAG7hy5JJx5DYfSiNwwNc'

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from analyzers.data_downloader import DataDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_collection.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Run full-scale NASDAQ data collection."""
    logger.info("🚀 BullsBears.xyz - Full-Scale NASDAQ Data Collection")
    logger.info("=" * 60)
    
    # Check environment
    if not os.getenv('DATABENTO_API_KEY'):
        logger.error("❌ DATABENTO_API_KEY environment variable not found!")
        logger.error("Please set your Databento API key in .env file")
        return False
    
    try:
        # Initialize downloader with 6 months of data
        downloader = DataDownloader(
            start_date="2024-05-01",  # 6 months back
            end_date="2024-11-02",    # Current date
            batch_size=50,            # Conservative batch size
            output_dir="data/backtest"
        )
        
        logger.info("📊 Configuration:")
        logger.info(f"   📅 Date range: {downloader.start_date} to {downloader.end_date}")
        logger.info(f"   📦 Batch size: {downloader.batch_size}")
        logger.info(f"   💾 Output directory: {downloader.output_dir}")
        logger.info(f"   🔑 Databento API: {'✅ Available' if downloader.use_databento else '❌ Not available'}")
        
        # Start data collection
        start_time = datetime.now()
        logger.info(f"⏰ Starting data collection at {start_time}")
        
        # Run full NASDAQ dataset download
        stats = await downloader.download_full_nasdaq_dataset()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Print final summary
        logger.info("=" * 60)
        logger.info("🎉 DATA COLLECTION COMPLETED!")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total duration: {duration}")
        logger.info(f"📊 Total tickers processed: {stats.get('total_tickers', 0)}")
        logger.info(f"✅ Successful downloads: {stats.get('successful_downloads', 0)}")
        logger.info(f"❌ Failed downloads: {stats.get('failed_downloads', 0)}")
        logger.info(f"📈 Success rate: {stats.get('success_rate', 0):.1f}%")
        logger.info(f"🔥 Databento successes: {stats.get('databento_success', 0)}")
        logger.info(f"🔄 yfinance fallbacks: {stats.get('yfinance_fallback', 0)}")
        
        # Check if we have enough data for ML training
        successful = stats.get('successful_downloads', 0)
        if successful >= 1000:
            logger.info("🎯 SUCCESS: Sufficient data collected for ML training!")
        elif successful >= 500:
            logger.info("⚠️  WARNING: Moderate data collected. Consider expanding dataset.")
        else:
            logger.info("❌ ERROR: Insufficient data for reliable ML training.")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Data collection failed: {e}")
        logger.exception("Full error traceback:")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🚀 Ready for next phase: Move detection and ML training!")
        sys.exit(0)
    else:
        logger.error("💥 Data collection failed. Check logs for details.")
        sys.exit(1)
