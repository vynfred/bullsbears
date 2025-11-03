#!/usr/bin/env python3
"""
Test Databento API integration
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_databento_connection():
    """Test basic Databento connection and data retrieval."""
    
    print("🔍 Testing Databento Integration...")
    print("=" * 60)
    
    # Check if API key is available
    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("❌ DATABENTO_API_KEY environment variable not found")
        print("💡 Please set your Databento API key:")
        print("   export DATABENTO_API_KEY='your_api_key_here'")
        return False
    
    print(f"✅ API key found: {api_key[:8]}...")
    
    try:
        import databento as db
        print("✅ Databento package imported successfully")
    except ImportError:
        print("❌ Databento package not installed")
        print("💡 Install with: pip install databento")
        return False
    
    try:
        # Initialize client
        client = db.Historical(api_key)
        print("✅ Databento client initialized")
        
        # Test with a simple ticker
        test_ticker = "AAPL"
        start_date = "2024-10-01"
        end_date = "2024-11-01"
        
        print(f"🔄 Testing data download for {test_ticker} ({start_date} to {end_date})...")
        
        # Try NASDAQ dataset first
        try:
            data = client.timeseries.get_range(
                dataset="XNAS.ITCH",
                symbols=[test_ticker],
                schema="ohlcv-1d",
                start=start_date,
                end=end_date,
                stype_in="raw_symbol"
            )
            
            if data is not None:
                df = data.to_df()
                if not df.empty:
                    print(f"✅ Successfully downloaded {len(df)} days of data for {test_ticker}")
                    print(f"📊 Data shape: {df.shape}")
                    print(f"📅 Date range: {df.index.min()} to {df.index.max()}")
                    print(f"🏷️  Columns: {list(df.columns)}")
                    print("\n📈 Sample data (first 3 rows):")
                    print(df.head(3))
                    return True
                else:
                    print(f"❌ No data returned for {test_ticker}")
            else:
                print(f"❌ No data object returned for {test_ticker}")
                
        except Exception as e:
            print(f"❌ NASDAQ dataset failed: {e}")
            
            # Try NYSE dataset as fallback
            try:
                print("🔄 Trying NYSE dataset...")
                data = client.timeseries.get_range(
                    dataset="XNYS.TRADES",
                    symbols=[test_ticker],
                    schema="ohlcv-1d", 
                    start=start_date,
                    end=end_date,
                    stype_in="raw_symbol"
                )
                
                if data is not None:
                    df = data.to_df()
                    if not df.empty:
                        print(f"✅ Successfully downloaded {len(df)} days from NYSE dataset")
                        return True
                        
            except Exception as e2:
                print(f"❌ NYSE dataset also failed: {e2}")
        
        return False
        
    except Exception as e:
        print(f"❌ Databento connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_databento_connection())
    if success:
        print("\n🎉 Databento integration test PASSED!")
    else:
        print("\n💥 Databento integration test FAILED!")
        print("💡 Please check your API key and network connection")
