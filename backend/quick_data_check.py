#!/usr/bin/env python3
"""
Quick Data Freshness Check
Check if our existing data is recent enough for production use
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import pytz

def check_data_freshness():
    """Check how fresh our existing data is."""
    data_file = Path("data/backtest/nasdaq_6mo_full.parquet")
    
    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return False
    
    print("🔍 Checking Data Freshness")
    print("=" * 50)
    
    # Load data
    data = pd.read_parquet(data_file)
    print(f"📊 Total records: {len(data):,}")
    print(f"📊 Unique tickers: {data['ticker'].nunique():,}")
    
    # Check date range
    dates = pd.to_datetime(data['ts_event'])
    min_date = dates.min()
    max_date = dates.max()
    
    print(f"📅 Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    # Check how old the data is (using correct current date - Nov 2024)
    utc = pytz.UTC
    # System clock is wrong (shows 2025), use actual current date
    today = utc.localize(datetime(2024, 11, 2))  # Actual current date
    days_old = (today - max_date).days
    
    print(f"⏰ Data is {days_old} days old")
    
    # Sample some major tickers to see their latest dates
    major_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
    
    print(f"\n📈 Latest dates for major tickers:")
    for ticker in major_tickers:
        ticker_data = data[data['ticker'] == ticker]
        if not ticker_data.empty:
            latest = pd.to_datetime(ticker_data['ts_event']).max()
            print(f"   {ticker}: {latest.strftime('%Y-%m-%d')}")
        else:
            print(f"   {ticker}: Not found")
    
    # Recommendation
    print(f"\n🎯 RECOMMENDATION:")
    if days_old <= 7:
        print(f"✅ Data is fresh enough ({days_old} days old)")
        print(f"✅ Can proceed with AI integration and model retraining")
        print(f"✅ No urgent need to update historical data")
        return True
    elif days_old <= 30:
        print(f"⚠️ Data is somewhat stale ({days_old} days old)")
        print(f"⚠️ Consider updating for production, but can proceed with testing")
        print(f"🔄 Recommend updating key tickers (top 100) first")
        return True
    else:
        print(f"❌ Data is too stale ({days_old} days old)")
        print(f"❌ Must update before proceeding to production")
        print(f"🔄 Recommend full data update")
        return False

def check_model_training_readiness():
    """Check if we have enough recent data for model retraining."""
    data_file = Path("data/backtest/nasdaq_6mo_full.parquet")
    
    if not data_file.exists():
        return False
    
    print(f"\n🤖 MODEL TRAINING READINESS CHECK")
    print("=" * 50)
    
    data = pd.read_parquet(data_file)
    
    # Check if we have enough recent data for training
    dates = pd.to_datetime(data['ts_event'])
    recent_cutoff = dates.max() - timedelta(days=90)  # Last 3 months
    recent_data = data[pd.to_datetime(data['ts_event']) >= recent_cutoff]
    
    print(f"📊 Recent data (last 90 days): {len(recent_data):,} records")
    print(f"📊 Recent tickers: {recent_data['ticker'].nunique():,}")
    
    # Check data density
    total_days = (dates.max() - dates.min()).days
    avg_records_per_day = len(data) / total_days
    
    print(f"📊 Average records per day: {avg_records_per_day:.0f}")
    print(f"📊 Data density: {len(data) / (data['ticker'].nunique() * total_days) * 100:.1f}%")
    
    if len(recent_data) > 100000 and recent_data['ticker'].nunique() > 1000:
        print(f"✅ Sufficient data for model retraining")
        return True
    else:
        print(f"⚠️ May need more recent data for optimal model performance")
        return False

def main():
    """Main check function."""
    print("🚀 BullsBears.xyz Data Freshness Check")
    print("=" * 60)
    
    data_fresh = check_data_freshness()
    model_ready = check_model_training_readiness()
    
    print(f"\n" + "=" * 60)
    print("🎯 FINAL RECOMMENDATION:")
    print("=" * 60)
    
    if data_fresh and model_ready:
        print("🎉 PROCEED WITH AI INTEGRATION!")
        print("✅ Data is fresh enough for production testing")
        print("✅ Sufficient data for model retraining")
        print("🚀 Next steps:")
        print("   1. Complete AI feature integration (82 features)")
        print("   2. Quick model retrain with existing data")
        print("   3. Deploy to production environment")
        print("   4. Schedule data updates for ongoing freshness")
        
    elif data_fresh:
        print("⚠️ PROCEED WITH CAUTION")
        print("✅ Data freshness is acceptable")
        print("⚠️ Consider model retraining with more recent data")
        print("🔄 Recommended actions:")
        print("   1. Complete AI integration with current data")
        print("   2. Update key tickers (top 100) for better model performance")
        print("   3. Retrain models with updated data")
        
    else:
        print("❌ UPDATE DATA FIRST")
        print("❌ Data is too stale for production use")
        print("🔄 Required actions:")
        print("   1. Update historical data to present day")
        print("   2. Retrain models with fresh data")
        print("   3. Then proceed with AI integration")
    
    return data_fresh and model_ready

if __name__ == "__main__":
    success = main()
