#!/usr/bin/env python3
"""
Full-Scale Move Detection Script
Analyzes 6 months of NASDAQ data to identify +20%/-20% moves for ML training.
"""

import asyncio
import logging
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from analyzers.move_detector import MoveDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('move_detection.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Run full-scale move detection on NASDAQ dataset."""
    logger.info("🎯 BullsBears.xyz - Full-Scale Move Detection")
    logger.info("=" * 60)
    
    try:
        # Check if data file exists
        data_file = Path("data/backtest/nasdaq_6mo_full.pkl")
        if not data_file.exists():
            logger.error(f"❌ Data file not found: {data_file}")
            logger.error("Please run full data collection first: python run_full_data_collection.py")
            return False
        
        logger.info(f"📊 Loading data from: {data_file}")
        
        # Load the full dataset
        try:
            data = pd.read_pickle(data_file)
            logger.info(f"✅ Loaded data shape: {data.shape}")
            logger.info(f"📅 Date range: {data.index.min()} to {data.index.max()}")
            
            # Get unique tickers
            tickers = data.columns.get_level_values(0).unique().tolist()
            logger.info(f"🎯 Found {len(tickers)} tickers in dataset")
            
        except Exception as e:
            logger.error(f"❌ Failed to load data: {e}")
            return False
        
        # Initialize move detector
        detector = MoveDetector(
            data_file="data/backtest/nasdaq_6mo_full.pkl",
            moon_threshold=20.0,  # +20% for moon events
            rug_threshold=-20.0,  # -20% for rug events
            max_days=3,     # Within 1-3 days
            min_volume=100000     # Minimum volume filter
        )
        
        logger.info("🔍 Configuration:")
        logger.info(f"   🌙 Moon threshold: +{detector.moon_threshold:.0f}%")
        logger.info(f"   💥 Rug threshold: {detector.rug_threshold:.0f}%")
        logger.info(f"   ⏰ Timeframe: {detector.max_days} days")
        logger.info(f"   📊 Min volume: {detector.min_volume:,}")
        
        # Run move detection using the MoveDetector class
        start_time = datetime.now()
        logger.info(f"⏰ Starting move detection at {start_time}")

        # Use the built-in detect_all_moves method
        detector.data = data  # Set the data directly
        all_moon_events, all_rug_events = detector.detect_all_moves()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Save results
        if all_moon_events:
            moon_df = pd.DataFrame(all_moon_events)
            moon_file = Path("data/backtest/moon_events_full.csv")
            moon_df.to_csv(moon_file, index=False)
            logger.info(f"💾 Saved {len(all_moon_events)} moon events to {moon_file}")
        
        if all_rug_events:
            rug_df = pd.DataFrame(all_rug_events)
            rug_file = Path("data/backtest/rug_events_full.csv")
            rug_df.to_csv(rug_file, index=False)
            logger.info(f"💾 Saved {len(all_rug_events)} rug events to {rug_file}")
        
        # Print final summary
        logger.info("=" * 60)
        logger.info("🎉 MOVE DETECTION COMPLETED!")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total duration: {duration}")
        logger.info(f"📊 Tickers processed: {len(tickers)}")
        logger.info(f"🌙 Moon events found: {len(all_moon_events)}")
        logger.info(f"💥 Rug events found: {len(all_rug_events)}")
        logger.info(f"📈 Total significant moves: {len(all_moon_events) + len(all_rug_events)}")
        
        # Check if we have enough events for ML training
        total_events = len(all_moon_events) + len(all_rug_events)
        if total_events >= 1000:
            logger.info("🎯 SUCCESS: Sufficient events for robust ML training!")
        elif total_events >= 500:
            logger.info("⚠️  WARNING: Moderate events found. Consider expanding criteria.")
        else:
            logger.info("❌ ERROR: Insufficient events for reliable ML training.")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Move detection failed: {e}")
        logger.exception("Full error traceback:")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🚀 Ready for next phase: Feature extraction and ML training!")
        sys.exit(0)
    else:
        logger.error("💥 Move detection failed. Check logs for details.")
        sys.exit(1)
