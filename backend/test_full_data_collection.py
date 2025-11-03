#!/usr/bin/env python3
"""
Test Full Data Collection with Small Sample
Tests the full-scale data collection pipeline with a small sample of tickers.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from analyzers.data_downloader import DataDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def test_nasdaq_ticker_loading():
    """Test loading NASDAQ tickers from CSV."""
    logger.info("🧪 Testing NASDAQ ticker loading...")
    
    downloader = DataDownloader()
    
    try:
        tickers = downloader.load_nasdaq_tickers()
        logger.info(f"✅ Successfully loaded {len(tickers)} valid NASDAQ tickers")
        logger.info(f"📊 Sample tickers: {tickers[:10]}")
        return tickers
    except Exception as e:
        logger.error(f"❌ Failed to load NASDAQ tickers: {e}")
        return None


async def test_small_batch_download(tickers, sample_size=10):
    """Test downloading a small batch of tickers."""
    logger.info(f"🧪 Testing small batch download ({sample_size} tickers)...")
    
    # Take a sample of tickers
    sample_tickers = tickers[:sample_size]
    logger.info(f"📊 Sample tickers: {sample_tickers}")
    
    downloader = DataDownloader(
        start_date="2024-10-01",  # Just 1 month for testing
        end_date="2024-11-02",
        batch_size=5,
        output_dir="data/test"
    )
    
    try:
        start_time = datetime.now()
        data = await downloader.download_all_tickers(sample_tickers)
        end_time = datetime.now()
        
        duration = end_time - start_time
        success_rate = len(data) / len(sample_tickers) * 100
        
        logger.info(f"✅ Downloaded {len(data)}/{len(sample_tickers)} tickers ({success_rate:.1f}%)")
        logger.info(f"⏱️  Duration: {duration}")
        
        # Show sample data
        if data:
            sample_ticker = list(data.keys())[0]
            sample_data = data[sample_ticker]
            logger.info(f"📊 Sample data for {sample_ticker}:")
            logger.info(f"   Shape: {sample_data.shape}")
            logger.info(f"   Date range: {sample_data.index.min()} to {sample_data.index.max()}")
            logger.info(f"   Columns: {list(sample_data.columns)}")
        
        return len(data) > 0
        
    except Exception as e:
        logger.error(f"❌ Small batch download failed: {e}")
        logger.exception("Full error traceback:")
        return False


async def main():
    """Run the test suite."""
    logger.info("🧪 BullsBears.xyz - Data Collection Test Suite")
    logger.info("=" * 60)
    
    # Check environment
    if not os.getenv('DATABENTO_API_KEY'):
        logger.error("❌ DATABENTO_API_KEY environment variable not found!")
        return False
    
    logger.info("✅ DATABENTO_API_KEY is set")
    
    # Test 1: Load NASDAQ tickers
    tickers = await test_nasdaq_ticker_loading()
    if not tickers:
        logger.error("❌ Failed to load tickers. Cannot proceed with tests.")
        return False
    
    # Test 2: Small batch download
    success = await test_small_batch_download(tickers, sample_size=10)
    if not success:
        logger.error("❌ Small batch download failed.")
        return False
    
    logger.info("=" * 60)
    logger.info("🎉 ALL TESTS PASSED!")
    logger.info("✅ Ready to run full-scale data collection")
    logger.info("🚀 Next step: python3 run_full_data_collection.py")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🎯 Test suite completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Test suite failed. Check configuration.")
        sys.exit(1)
