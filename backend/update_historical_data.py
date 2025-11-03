#!/usr/bin/env python3
"""
Update Historical Data to Present Day
Updates existing dataset with recent data from Nov 2024 to Nov 2025
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from pathlib import Path
import pytz

# Add backend to path
sys.path.append('/Users/vynfred/Documents/bullsbears/backend')

from app.analyzers.data_downloader import DataDownloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoricalDataUpdater:
    def __init__(self):
        # Use timezone-aware datetimes to match existing data
        utc = pytz.UTC
        self.start_date = utc.localize(datetime(2024, 11, 2))  # Day after last data
        self.end_date = utc.localize(datetime(2025, 11, 2))    # Today
        self.batch_size = 50  # Process 50 tickers at a time

        # Data file paths
        self.data_dir = Path("data/backtest")
        self.existing_data_file = self.data_dir / "nasdaq_6mo_full.parquet"
        self.updated_data_file = self.data_dir / "nasdaq_6mo_full_updated.parquet"

        # Initialize data downloader with update date range
        self.data_downloader = DataDownloader(
            start_date=self.start_date.strftime('%Y-%m-%d'),
            end_date=self.end_date.strftime('%Y-%m-%d'),
            batch_size=self.batch_size
        )

    def load_existing_data(self) -> pd.DataFrame:
        """Load existing historical data from parquet file."""
        if not self.existing_data_file.exists():
            logger.error(f"❌ Existing data file not found: {self.existing_data_file}")
            return pd.DataFrame()

        logger.info(f"📂 Loading existing data from {self.existing_data_file}")
        existing_data = pd.read_parquet(self.existing_data_file)
        logger.info(f"📊 Loaded {len(existing_data)} existing records")

        # Show data summary
        if not existing_data.empty:
            tickers = existing_data['ticker'].unique()
            dates = pd.to_datetime(existing_data['ts_event'])
            logger.info(f"📈 Existing data: {len(tickers)} tickers, {dates.min()} to {dates.max()}")

        return existing_data

    def get_existing_tickers(self, existing_data: pd.DataFrame) -> List[str]:
        """Get list of tickers from existing data."""
        if existing_data.empty:
            return []

        tickers = existing_data['ticker'].unique().tolist()
        logger.info(f"📊 Found {len(tickers)} existing tickers")
        return tickers
    
    def get_latest_date_for_ticker(self, ticker: str, existing_data: pd.DataFrame) -> datetime:
        """Get the latest date for a specific ticker from existing data."""
        utc = pytz.UTC
        default_start = utc.localize(datetime(2024, 5, 1))

        if existing_data.empty:
            return default_start

        try:
            ticker_data = existing_data[existing_data['ticker'] == ticker]
            if ticker_data.empty:
                logger.warning(f"⚠️ No existing data for {ticker}")
                return default_start

            latest_date = pd.to_datetime(ticker_data['ts_event']).max()
            # Ensure timezone-aware
            if latest_date.tz is None:
                latest_date = utc.localize(latest_date)
            return latest_date.to_pydatetime()
        except Exception as e:
            logger.warning(f"⚠️ Error getting latest date for {ticker}: {e}")
            return default_start

    def get_missing_dates_for_ticker(self, ticker: str, existing_data: pd.DataFrame) -> List[datetime]:
        """Get list of missing dates for a specific ticker."""
        latest_date = self.get_latest_date_for_ticker(ticker, existing_data)

        # Calculate missing dates
        missing_dates = []
        current_date = latest_date + timedelta(days=1)

        while current_date <= self.end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        logger.info(f"📅 {ticker}: {len(missing_dates)} missing trading days from {latest_date.strftime('%Y-%m-%d')}")
        return missing_dates
    
    async def update_ticker_data(self, ticker: str, existing_data: pd.DataFrame) -> Dict[str, Any]:
        """Update data for a single ticker."""
        try:
            logger.info(f"🔄 Updating {ticker}...")

            # Get missing dates
            missing_dates = self.get_missing_dates_for_ticker(ticker, existing_data)

            if not missing_dates:
                logger.info(f"✅ {ticker}: Already up to date")
                return {"ticker": ticker, "status": "up_to_date", "new_records": 0, "data": None}

            # Download new data using DataDownloader
            logger.info(f"📡 Downloading {len(missing_dates)} days for {ticker}...")

            # Try Databento first, then yfinance fallback
            ticker_data = await self.data_downloader.download_databento_ticker(ticker)

            if ticker_data is None or ticker_data.empty:
                # Fallback to yfinance
                logger.info(f"🔄 Trying yfinance fallback for {ticker}...")
                ticker_data = await self.data_downloader.download_yfinance_fallback(ticker)

            if ticker_data is None or ticker_data.empty:
                logger.warning(f"⚠️ No new data received for {ticker}")
                return {"ticker": ticker, "status": "no_data", "new_records": 0, "data": None}

            # Filter to only new dates (after latest existing date)
            latest_date = self.get_latest_date_for_ticker(ticker, existing_data)
            ticker_data = ticker_data[ticker_data.index > latest_date]

            if ticker_data.empty:
                logger.info(f"✅ {ticker}: No new data after filtering")
                return {"ticker": ticker, "status": "up_to_date", "new_records": 0, "data": None}

            # Prepare data for merging (match existing data format)
            ticker_data = ticker_data.reset_index()
            ticker_data = ticker_data.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            ticker_data['ts_event'] = pd.to_datetime(ticker_data['date']).dt.tz_localize('UTC')
            ticker_data['ticker'] = ticker
            ticker_data = ticker_data[['ts_event', 'Open', 'High', 'Low', 'Close', 'Volume', 'ticker']]

            new_records = len(ticker_data)
            logger.info(f"✅ {ticker}: Downloaded {new_records} new records")

            return {
                "ticker": ticker,
                "status": "updated",
                "new_records": new_records,
                "data": ticker_data
            }

        except Exception as e:
            logger.error(f"❌ Error updating {ticker}: {e}")
            return {"ticker": ticker, "status": "error", "error": str(e), "new_records": 0, "data": None}
    
    async def update_all_data(self):
        """Update data for all existing tickers."""
        logger.info("🚀 Starting Historical Data Update")
        logger.info(f"📅 Update period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        logger.info("=" * 80)

        # Load existing data
        existing_data = self.load_existing_data()

        if existing_data.empty:
            logger.error("❌ No existing data found")
            return

        # Get existing tickers
        tickers = self.get_existing_tickers(existing_data)

        if not tickers:
            logger.error("❌ No existing tickers found")
            return

        # Process tickers in batches
        results = []
        total_new_records = 0
        all_new_data = []

        for i in range(0, len(tickers), self.batch_size):
            batch = tickers[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(tickers) + self.batch_size - 1) // self.batch_size

            logger.info(f"\n📦 Processing Batch {batch_num}/{total_batches}: {len(batch)} tickers")
            logger.info(f"🎯 Tickers: {', '.join(batch[:5])}{'...' if len(batch) > 5 else ''}")

            # Process batch concurrently
            batch_tasks = [self.update_ticker_data(ticker, existing_data) for ticker in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ Batch error: {result}")
                    continue

                results.append(result)
                if result.get("new_records", 0) > 0:
                    total_new_records += result["new_records"]

                    # Collect new data for merging
                    if result.get("data") is not None:
                        all_new_data.append(result["data"])

            # Progress update
            completed = len(results)
            logger.info(f"📊 Progress: {completed}/{len(tickers)} tickers processed")

            # Brief pause between batches
            if i + self.batch_size < len(tickers):
                await asyncio.sleep(1)
        
        # Merge new data with existing data
        if all_new_data:
            logger.info(f"\n🔄 Merging {len(all_new_data)} updated datasets...")

            # Combine all new data
            new_data_combined = pd.concat(all_new_data, axis=0)
            logger.info(f"📊 Combined new data: {len(new_data_combined)} records")

            # Merge with existing data
            updated_data = pd.concat([existing_data, new_data_combined], axis=0, ignore_index=True)

            # Remove duplicates based on ticker and ts_event (keep last)
            updated_data = updated_data.drop_duplicates(subset=['ticker', 'ts_event'], keep='last')

            # Sort by ticker and date
            updated_data = updated_data.sort_values(['ticker', 'ts_event']).reset_index(drop=True)

            logger.info(f"📊 Final dataset: {len(updated_data)} total records")

            # Save updated data
            logger.info(f"💾 Saving updated data to {self.updated_data_file}")
            updated_data.to_parquet(self.updated_data_file)

            # Also backup original and replace
            backup_file = self.data_dir / "nasdaq_6mo_full_backup.parquet"
            if self.existing_data_file.exists():
                logger.info(f"📦 Creating backup: {backup_file}")
                os.rename(self.existing_data_file, backup_file)

            logger.info(f"🔄 Replacing original file with updated data")
            os.rename(self.updated_data_file, self.existing_data_file)

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 HISTORICAL DATA UPDATE SUMMARY")
        logger.info("=" * 80)

        status_counts = {}
        for result in results:
            status = result.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            logger.info(f"📈 {status.upper()}: {count} tickers")

        logger.info(f"📊 Total new records added: {total_new_records:,}")
        logger.info(f"📅 Data now current through: {self.end_date.strftime('%Y-%m-%d')}")

        # Show sample of updated tickers
        updated_tickers = [r["ticker"] for r in results if r.get("status") == "updated"]
        if updated_tickers:
            logger.info(f"✅ Sample updated tickers: {', '.join(updated_tickers[:10])}")

        if total_new_records > 0:
            logger.info("🎉 HISTORICAL DATA UPDATE: COMPLETED SUCCESSFULLY!")
            logger.info("🚀 Ready for model retraining with fresh data")
        else:
            logger.info("ℹ️ No new data was needed - all tickers already current")

        return results

async def main():
    """Main execution function."""
    updater = HistoricalDataUpdater()
    results = await updater.update_all_data()
    return results

if __name__ == "__main__":
    results = asyncio.run(main())
