#!/usr/bin/env python3
"""
Check FMP API quota and estimate priming requirements
"""

import asyncio
import os
import sys
sys.path.append('.')

# Fix import - use correct class name
from app.services.fmp_data_ingestion import FMPDataIngestion, FMPConfig

async def check_fmp_quota():
    """Check FMP API and calculate priming requirements"""
    print("📊 FMP API QUOTA CHECK")
    print("=" * 50)
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY not found in environment")
        return False
    
    try:
        # Create FMP service with config
        config = FMPConfig(api_key=api_key)
        
        async with FMPDataIngestion(config) as fmp:
            # Test API connection
            nasdaq_stocks = await fmp.get_nasdaq_stocks()
            print(f"✅ FMP API Connected: {len(nasdaq_stocks)} NASDAQ stocks")
            
            # Calculate priming requirements
            stocks_count = len(nasdaq_stocks)
            months = 6
            
            # FMP historical endpoint: 1 call per stock for 6 months
            total_calls_needed = stocks_count
            
            print(f"\n📈 PRIMING REQUIREMENTS:")
            print(f"   Stocks: {stocks_count:,}")
            print(f"   Period: {months} months")
            print(f"   API Calls Needed: {total_calls_needed:,}")
            
            # Your quota
            calls_per_minute = 300
            minutes_needed = total_calls_needed / calls_per_minute
            hours_needed = minutes_needed / 60
            
            print(f"\n⏱️  TIME ESTIMATE:")
            print(f"   Your Quota: {calls_per_minute} calls/minute")
            print(f"   Time Needed: {minutes_needed:.1f} minutes ({hours_needed:.1f} hours)")
            
            if hours_needed > 2:
                print(f"⚠️  WARNING: Priming will take {hours_needed:.1f} hours")
                print("   Consider running overnight or in batches")
            else:
                print(f"✅ Reasonable time: {hours_needed:.1f} hours")
            
            return True
        
    except Exception as e:
        print(f"❌ FMP API test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(check_fmp_quota())
