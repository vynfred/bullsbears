#!/usr/bin/env python3
"""
Test script for the complete historical data collection pipeline.
Runs ticker processing, data download, and move detection.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.analyzers.ticker_processor import process_nasdaq_tickers
from app.analyzers.data_downloader import download_nasdaq_historical_data
from app.analyzers.move_detector import detect_nasdaq_moves

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_pipeline_test.log')
    ]
)
logger = logging.getLogger(__name__)


async def test_ticker_processing():
    """Test the NASDAQ ticker processing pipeline."""
    print("\n" + "="*60)
    print("🎯 STEP 1: NASDAQ Ticker Processing")
    print("="*60)
    
    try:
        result = await process_nasdaq_tickers()
        
        print(f"✅ Ticker processing completed successfully!")
        print(f"   Filtered tickers: {result['filtered_count']}")
        print(f"   Priority tickers: {result['priority_count']}")
        print(f"   Files saved: {list(result['saved_files'].keys())}")
        
        # Show some statistics
        if 'stats' in result:
            stats = result['stats']
            if 'sectors' in stats:
                print(f"\n📊 Top sectors:")
                for sector, count in list(stats['sectors'].items())[:5]:
                    print(f"   {sector}: {count} tickers")
            
            if 'market_cap_ranges' in stats:
                print(f"\n💰 Market cap distribution:")
                for range_name, count in stats['market_cap_ranges'].items():
                    print(f"   {range_name.replace('_', ' ').title()}: {count} tickers")
        
        return True
        
    except Exception as e:
        print(f"❌ Ticker processing failed: {e}")
        logger.error(f"Ticker processing failed: {e}", exc_info=True)
        return False


async def test_data_download(sample_mode: bool = False):
    """Test the historical data download pipeline."""
    print("\n" + "="*60)
    print("🎯 STEP 2: Historical Data Download")
    print("="*60)
    
    try:
        if sample_mode:
            print("🔬 Running in SAMPLE MODE (first 50 tickers only)")
            # Create a sample ticker file for testing
            sample_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'CRM', 'ADBE',
                'GME', 'AMC', 'HOOD', 'PLTR', 'COIN', 'RIVN', 'LCID', 'SPCE', 'SMCI', 'AVGO',
                'INTC', 'QCOM', 'AMD', 'NOW', 'SNOW', 'ARKK', 'SOXL', 'TQQQ', 'SQQQ', 'SPY',
                'QQQ', 'IWM', 'VTI', 'VOO', 'SCHD', 'JEPI', 'JEPQ', 'DIVO', 'DGRO', 'NOBL',
                'MRNA', 'PFE', 'JNJ', 'UNH', 'CVS', 'ABBV', 'BMY', 'LLY', 'TMO', 'DHR'
            ]
            
            # Save sample ticker file
            sample_file = Path("data/backtest/nasdaq_priority_tickers.txt")
            sample_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sample_file, 'w') as f:
                f.write('\n'.join(sample_tickers))
            
            print(f"📝 Created sample ticker file with {len(sample_tickers)} tickers")
        
        result = await download_nasdaq_historical_data()
        
        if result['output_file']:
            print(f"✅ Data download completed successfully!")
            print(f"   Output file: {result['output_file']}")
            print(f"   Tickers downloaded: {result['ticker_count']}")
            
            summary = result['summary']
            print(f"\n📊 Download Summary:")
            print(f"   Success rate: {summary['success_rate']:.1f}%")
            print(f"   Total tickers: {summary['total_tickers']}")
            print(f"   Successful: {summary['successful_downloads']}")
            print(f"   Failed: {summary['failed_downloads']}")
            print(f"   Duration: {summary['duration']}")
            
            if summary.get('databento_success', 0) > 0:
                print(f"   Databento successes: {summary['databento_success']}")
            if summary.get('yfinance_fallback', 0) > 0:
                print(f"   yfinance fallback: {summary['yfinance_fallback']}")
            
            return True
        else:
            print(f"❌ Data download failed - no output file created")
            return False
        
    except Exception as e:
        print(f"❌ Data download failed: {e}")
        logger.error(f"Data download failed: {e}", exc_info=True)
        return False


async def test_move_detection():
    """Test the move detection pipeline."""
    print("\n" + "="*60)
    print("🎯 STEP 3: Move Detection and Labeling")
    print("="*60)
    
    try:
        result = await detect_nasdaq_moves()
        
        print(f"✅ Move detection completed successfully!")
        print(f"   Moon events: {result['moon_events']}")
        print(f"   Rug events: {result['rug_events']}")
        
        # Show event statistics
        if 'event_stats' in result:
            stats = result['event_stats']
            print(f"\n📊 Event Statistics:")
            print(f"   Total events: {stats['total_events']}")
            
            if 'moon_stats' in stats:
                moon_stats = stats['moon_stats']
                print(f"\n🌙 Moon Event Stats:")
                print(f"   Average return: {moon_stats['avg_return']:.1f}%")
                print(f"   Maximum return: {moon_stats['max_return']:.1f}%")
                print(f"   Average days: {moon_stats['avg_days']:.1f}")
                print(f"   Day distribution: {moon_stats['day_distribution']}")
            
            if 'rug_stats' in stats:
                rug_stats = stats['rug_stats']
                print(f"\n💥 Rug Event Stats:")
                print(f"   Average return: {rug_stats['avg_return']:.1f}%")
                print(f"   Minimum return: {rug_stats['min_return']:.1f}%")
                print(f"   Average days: {rug_stats['avg_days']:.1f}")
                print(f"   Day distribution: {rug_stats['day_distribution']}")
        
        # Show save statistics
        if 'save_stats' in result:
            save_stats = result['save_stats']
            print(f"\n💾 Files Saved:")
            print(f"   Moon events: {save_stats['moon_events']}")
            print(f"   Rug events: {save_stats['rug_events']}")
            print(f"   High-confidence moon: {save_stats['high_conf_moon']}")
            print(f"   High-confidence rug: {save_stats['high_conf_rug']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Move detection failed: {e}")
        logger.error(f"Move detection failed: {e}", exc_info=True)
        return False


async def test_backtesting():
    """Test the backtesting engine with detected events."""
    try:
        print("============================================================")
        print("🎯 STEP 4: Backtesting Engine")
        print("============================================================")

        from app.analyzers.backtest import BacktestEngine

        # Initialize backtesting engine
        engine = BacktestEngine()

        # Load historical data
        data_file = "data/backtest/nasdaq_3mo.pkl"
        if not Path(data_file).exists():
            print(f"❌ Historical data file not found: {data_file}")
            print("💡 Run step 2 first to download historical data")
            return False

        print(f"📊 Loading historical data from {data_file}...")

        # Load the data to get ticker symbols
        import pickle
        with open(data_file, 'rb') as f:
            data = pickle.load(f)

        # Extract ticker symbols from the multi-level columns
        if hasattr(data.columns, 'levels'):
            symbols = list(data.columns.levels[0])
        else:
            # Fallback: extract from column names
            symbols = list(set([col.split('_')[0] if '_' in col else col for col in data.columns]))

        print(f"📈 Found {len(symbols)} symbols in dataset")

        # Run moon backtesting
        print("🌙 Running moon pattern backtesting...")
        moon_results = await engine.backtest_moon(symbols[:10])  # Test with first 10 symbols

        print(f"✅ Moon backtesting completed!")
        print(f"   Patterns detected: {len(moon_results)}")

        # Run rug backtesting
        print("\n💥 Running rug pattern backtesting...")
        rug_results = await engine.backtest_rug(symbols[:10])  # Test with first 10 symbols

        print(f"✅ Rug backtesting completed!")
        print(f"   Patterns detected: {len(rug_results)}")

        # Summary
        total_patterns = len(moon_results) + len(rug_results)

        print(f"\n📊 Backtesting Summary:")
        print(f"   Total patterns: {total_patterns}")
        print(f"   Moon patterns: {len(moon_results)}")
        print(f"   Rug patterns: {len(rug_results)}")
        print(f"   Test symbols: {len(symbols[:10])}")

        return True

    except Exception as e:
        print(f"❌ Backtesting failed: {e}")
        logger.error(f"Backtesting failed: {e}", exc_info=True)
        return False


async def run_full_pipeline(sample_mode: bool = False):
    """Run the complete data collection pipeline."""
    print("🚀 BullsBears Historical Data Collection Pipeline")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if sample_mode:
        print("🔬 RUNNING IN SAMPLE MODE - Limited dataset for testing")
    
    print("="*80)
    
    # Step 1: Process tickers
    step1_success = await test_ticker_processing()
    if not step1_success:
        print("\n❌ Pipeline failed at Step 1 (Ticker Processing)")
        return False
    
    # Step 2: Download data
    step2_success = await test_data_download(sample_mode=sample_mode)
    if not step2_success:
        print("\n❌ Pipeline failed at Step 2 (Data Download)")
        return False
    
    # Step 3: Detect moves
    step3_success = await test_move_detection()
    if not step3_success:
        print("\n❌ Pipeline failed at Step 3 (Move Detection)")
        return False
    
    # Success summary
    print("\n" + "="*80)
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*80)
    
    print("\n📁 Generated Files:")
    data_dir = Path("data/backtest")
    if data_dir.exists():
        for file in data_dir.glob("*"):
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"   {file.name} ({size_mb:.1f} MB)")
    
    print("\n📝 Next Steps:")
    print("   1. Review generated event files for data quality")
    print("   2. Run feature extraction on detected events")
    print("   3. Train ML models using the labeled data")
    print("   4. Validate model accuracy with backtesting")
    print("   5. Deploy to production for live scanning")
    
    return True


async def main():
    """Main test function with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test BullsBears data collection pipeline")
    parser.add_argument("--sample", action="store_true", 
                       help="Run in sample mode with limited tickers for testing")
    parser.add_argument("--step", choices=['1', '2', '3', '4'],
                       help="Run only a specific step (1=tickers, 2=download, 3=moves, 4=backtest)")
    
    args = parser.parse_args()
    
    try:
        if args.step == '1':
            success = await test_ticker_processing()
        elif args.step == '2':
            success = await test_data_download(sample_mode=args.sample)
        elif args.step == '3':
            success = await test_move_detection()
        elif args.step == '4':
            success = await test_backtesting()
        else:
            success = await run_full_pipeline(sample_mode=args.sample)
        
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Pipeline failed with unexpected error: {e}")
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
