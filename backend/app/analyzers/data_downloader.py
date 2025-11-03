"""
Multi-Source Historical Data Downloader
Downloads OHLCV data using yfinance (primary) and Databento (backup) for backtesting.
"""

import asyncio
import pandas as pd
import yfinance as yf
import logging
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import pickle
from concurrent.futures import ThreadPoolExecutor
import aiohttp

# Databento import (optional)
try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    logging.warning("Databento not installed. Using yfinance only.")

logger = logging.getLogger(__name__)


class DataDownloader:
    """Databento-primary historical data downloader for backtesting."""

    def __init__(self,
                 start_date: str = "2024-05-01",  # 6 months of data
                 end_date: str = "2024-11-02",
                 batch_size: int = 50,  # Smaller batches for full-scale processing
                 output_dir: str = "data/backtest"):

        self.start_date = start_date
        self.end_date = end_date
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Databento client (primary source)
        self.databento_client = None
        self.use_databento = False

        if DATABENTO_AVAILABLE:
            api_key = os.getenv('DATABENTO_API_KEY')
            if api_key:
                try:
                    self.databento_client = db.Historical(api_key)
                    self.use_databento = True
                    logger.info("✅ Databento client initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize Databento client: {e}")
                    logger.info("📉 Falling back to yfinance-only mode")
            else:
                logger.warning("DATABENTO_API_KEY environment variable not found")
                logger.info("📉 Using yfinance-only mode")
        else:
            logger.warning("Databento package not installed")
            logger.info("📉 Using yfinance-only mode")

        self.download_stats = {
            'total_tickers': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'databento_success': 0,
            'yfinance_fallback': 0,
            'start_time': None,
            'end_time': None
        }
    
    def load_ticker_list(self, ticker_file: str = "data/backtest/nasdaq_priority_tickers.txt") -> List[str]:
        """Load ticker list from file."""
        ticker_path = Path(ticker_file)
        if not ticker_path.exists():
            logger.error(f"Ticker file not found: {ticker_path}")
            raise FileNotFoundError(f"Ticker file not found: {ticker_path}")

        with open(ticker_path, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]

        logger.info(f"Loaded {len(tickers)} tickers from {ticker_path}")
        return tickers

    def load_nasdaq_tickers(self, csv_file: str = "../Data/nasdaq_screener_1762100638908.csv") -> List[str]:
        """Load all NASDAQ tickers from the screener CSV file."""
        csv_path = Path(csv_file)
        if not csv_path.exists():
            logger.error(f"NASDAQ CSV file not found: {csv_path}")
            raise FileNotFoundError(f"NASDAQ CSV file not found: {csv_path}")

        try:
            df = pd.read_csv(csv_path)
            # Filter out invalid tickers (SPACs, warrants, units)
            valid_tickers = []

            for _, row in df.iterrows():
                symbol = str(row['Symbol']) if pd.notna(row['Symbol']) else ""
                name = str(row['Name']) if pd.notna(row['Name']) else ""

                # Convert market cap and volume to float, handle NaN
                try:
                    market_cap = float(row['Market Cap']) if pd.notna(row['Market Cap']) else 0
                except (ValueError, TypeError):
                    market_cap = 0

                try:
                    volume = float(row['Volume']) if pd.notna(row['Volume']) else 0
                except (ValueError, TypeError):
                    volume = 0

                # Skip empty symbols
                if not symbol:
                    continue

                # Skip invalid tickers
                if (symbol.endswith('.U') or symbol.endswith('.WS') or
                    symbol.endswith('W') or symbol.endswith('R') or
                    'warrant' in name.lower() or 'unit' in name.lower() or
                    'spac' in name.lower() or 'acquisition' in name.lower()):
                    continue

                # Skip low volume or low market cap stocks
                if market_cap < 100_000_000 or volume < 100_000:  # $100M market cap, 100K volume
                    continue

                valid_tickers.append(symbol)

            logger.info(f"Loaded {len(valid_tickers)} valid tickers from {len(df)} total NASDAQ stocks")
            logger.info(f"Filtered out {len(df) - len(valid_tickers)} invalid/low-volume tickers")

            return valid_tickers

        except Exception as e:
            logger.error(f"Error loading NASDAQ tickers: {e}")
            raise
    
    async def download_databento_batch(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """Download data for a batch of tickers using Databento."""
        logger.info(f"Downloading batch of {len(tickers)} tickers via Databento...")

        ticker_data = {}

        try:
            # Use ThreadPoolExecutor to run Databento API calls in separate threads
            loop = asyncio.get_event_loop()

            # Process tickers individually for better error handling
            for ticker in tickers:
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        data = await loop.run_in_executor(
                            executor,
                            self._databento_download,
                            ticker
                        )

                    if data is not None and not data.empty and len(data) > 10:
                        ticker_data[ticker] = data
                        self.download_stats['databento_success'] += 1
                        logger.debug(f"✅ {ticker}: {len(data)} days downloaded")
                    else:
                        logger.warning(f"❌ {ticker}: No data or insufficient data")
                        self.download_stats['failed_downloads'] += 1

                    # Small delay between requests to be respectful
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"❌ {ticker}: Download failed - {e}")
                    self.download_stats['failed_downloads'] += 1

            logger.info(f"Databento batch complete: {len(ticker_data)}/{len(tickers)} successful downloads")
            return ticker_data

        except Exception as e:
            logger.error(f"Databento batch download failed: {e}")
            return {}
    
    def _yfinance_download(self, tickers: List[str]) -> Optional[pd.DataFrame]:
        """Synchronous yfinance download (runs in thread)."""
        try:
            if len(tickers) == 1:
                # Single ticker download
                ticker_obj = yf.Ticker(tickers[0])
                data = ticker_obj.history(
                    start=self.start_date,
                    end=self.end_date,
                    auto_adjust=True,
                    prepost=False
                )
            else:
                # Multi-ticker download
                data = yf.download(
                    tickers,
                    start=self.start_date,
                    end=self.end_date,
                    group_by='ticker',
                    auto_adjust=True,
                    prepost=False,
                    progress=False
                )
            
            # Add small delay to be respectful to Yahoo Finance
            time.sleep(0.5)
            return data
            
        except Exception as e:
            logger.error(f"yfinance download error: {e}")
            return None
    
    async def download_databento_ticker(self, ticker: str) -> Optional[pd.DataFrame]:
        """Download data for a single ticker using Databento."""
        if not self.databento_client:
            return None
        
        try:
            logger.debug(f"Downloading {ticker} via Databento...")
            
            # Use ThreadPoolExecutor for Databento API call
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                data = await loop.run_in_executor(
                    executor,
                    self._databento_download,
                    ticker
                )
            
            if data is not None and not data.empty:
                self.download_stats['databento_success'] += 1
                return data
            
        except Exception as e:
            logger.error(f"Databento download failed for {ticker}: {e}")
        
        return None
    
    def _databento_download(self, ticker: str) -> Optional[pd.DataFrame]:
        """Synchronous Databento download (runs in thread)."""
        try:
            # Download daily bars from Databento
            # Try multiple datasets for better coverage
            datasets_to_try = [
                "XNAS.ITCH",  # NASDAQ
                "XNYS.TRADES",  # NYSE
                "OPRA.PILLAR",  # Options (if needed)
            ]

            for dataset in datasets_to_try:
                try:
                    data = self.databento_client.timeseries.get_range(
                        dataset=dataset,
                        symbols=[ticker],
                        schema="ohlcv-1d",
                        start=self.start_date,
                        end=self.end_date,
                        stype_in="raw_symbol"
                    )

                    if data is not None:
                        # Convert to pandas DataFrame
                        df = data.to_df()
                        if not df.empty:
                            # Ensure we have the required columns
                            required_cols = ['open', 'high', 'low', 'close', 'volume']
                            if all(col in df.columns for col in required_cols):
                                # Rename columns to match expected format
                                df = df.rename(columns={
                                    'open': 'Open',
                                    'high': 'High',
                                    'low': 'Low',
                                    'close': 'Close',
                                    'volume': 'Volume'
                                })

                                # Set timestamp as index
                                if 'ts_event' in df.columns:
                                    df.index = pd.to_datetime(df['ts_event'])
                                    df = df.drop(columns=['ts_event'], errors='ignore')
                                elif df.index.name != 'ts_event':
                                    # If index is already datetime, keep it
                                    pass

                                # Clean up the data
                                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()

                                if len(df) > 0:
                                    logger.debug(f"✅ {ticker}: Found {len(df)} days in {dataset}")
                                    return df

                except Exception as dataset_error:
                    logger.debug(f"Dataset {dataset} failed for {ticker}: {dataset_error}")
                    continue

            logger.warning(f"No data found for {ticker} in any dataset")
            return None

        except Exception as e:
            logger.error(f"Databento API error for {ticker}: {e}")
            return None
    
    async def download_yfinance_fallback(self, ticker: str) -> Optional[pd.DataFrame]:
        """Download ticker data using yfinance as fallback."""
        try:
            logger.info(f"Trying yfinance fallback for {ticker}...")

            # Use ThreadPoolExecutor for yfinance
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                data = await loop.run_in_executor(
                    executor,
                    self._yfinance_download_single,
                    ticker
                )

            if data is not None and not data.empty and len(data) > 10:
                self.download_stats['yfinance_fallback'] += 1
                return data

        except Exception as e:
            logger.error(f"yfinance fallback failed for {ticker}: {e}")

        return None

    def _yfinance_download_single(self, ticker: str) -> Optional[pd.DataFrame]:
        """Download single ticker using yfinance."""
        try:
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(
                start=self.start_date,
                end=self.end_date,
                auto_adjust=True,
                prepost=False
            )

            if not data.empty:
                # Ensure we have the required columns
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                if all(col in data.columns for col in required_cols):
                    return data[required_cols].dropna()

        except Exception as e:
            logger.error(f"yfinance single download error for {ticker}: {e}")

        return None
    
    async def download_all_tickers(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """Download data for all tickers using Databento primary, yfinance fallback."""
        self.download_stats['total_tickers'] = len(tickers)
        self.download_stats['start_time'] = datetime.now()

        logger.info(f"Starting download of {len(tickers)} tickers using Databento...")

        all_data = {}

        # Process in batches
        for i in range(0, len(tickers), self.batch_size):
            batch = tickers[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(tickers) - 1) // self.batch_size + 1

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

            # Use Databento as primary source
            batch_data = await self.download_databento_batch(batch)

            # For failed tickers, try yfinance fallback
            failed_tickers = [t for t in batch if t not in batch_data]
            if failed_tickers:
                logger.info(f"Trying yfinance fallback for {len(failed_tickers)} failed tickers...")
                for ticker in failed_tickers:
                    ticker_data = await self.download_yfinance_fallback(ticker)
                    if ticker_data is not None:
                        batch_data[ticker] = ticker_data

            all_data.update(batch_data)

            # Progress update
            success_rate = len(all_data) / len(tickers) * 100
            logger.info(f"Batch {batch_num} complete. Overall progress: {len(all_data)}/{len(tickers)} ({success_rate:.1f}%)")

            # Rate limiting delay between batches to be respectful to APIs
            if i + self.batch_size < len(tickers):
                await asyncio.sleep(3)

        self.download_stats['successful_downloads'] = len(all_data)
        self.download_stats['failed_downloads'] = len(tickers) - len(all_data)
        self.download_stats['end_time'] = datetime.now()
        self.download_stats['duration'] = str(self.download_stats['end_time'] - self.download_stats['start_time'])
        self.download_stats['success_rate'] = len(all_data) / len(tickers) * 100 if tickers else 0

        logger.info("Historical data download completed!")
        logger.info(f"Summary: {self.download_stats}")

        return all_data

    async def download_full_nasdaq_dataset(self) -> Dict[str, Any]:
        """Download full NASDAQ dataset with 6 months of historical data."""
        logger.info("🚀 Starting full-scale NASDAQ data collection...")
        logger.info(f"📅 Date range: {self.start_date} to {self.end_date}")
        logger.info(f"📊 Target: All valid NASDAQ stocks with 6 months of data")

        # Load all NASDAQ tickers
        tickers = self.load_nasdaq_tickers()
        if not tickers:
            raise ValueError("No valid NASDAQ tickers found")

        logger.info(f"🎯 Processing {len(tickers)} valid NASDAQ tickers")
        logger.info(f"📦 Batch size: {self.batch_size} tickers per batch")
        logger.info(f"⏱️ Estimated time: {len(tickers) // self.batch_size * 3 / 60:.1f} minutes")

        # Download all tickers
        all_data = await self.download_all_tickers(tickers)

        # Save data with compression
        if all_data:
            # Save as Parquet for better compression and performance
            output_file = self.output_dir / "nasdaq_6mo_full.parquet"
            self._save_data_parquet(all_data, output_file)

            # Also save as pickle for backward compatibility
            pickle_file = self.output_dir / "nasdaq_6mo_full.pkl"
            self.save_data(all_data, pickle_file.name)

            logger.info(f"✅ Saved {len(all_data)} tickers to {output_file}")
            logger.info(f"📈 Success rate: {len(all_data)/len(tickers)*100:.1f}%")
        else:
            logger.warning("❌ No data to save")

        return self.download_stats

    def _save_data_parquet(self, data: Dict[str, pd.DataFrame], output_file: Path):
        """Save data in Parquet format for better compression."""
        try:
            # Combine all ticker data into a single DataFrame
            combined_data = []
            for ticker, df in data.items():
                df_copy = df.copy()
                df_copy['ticker'] = ticker
                df_copy.reset_index(inplace=True)
                combined_data.append(df_copy)

            if combined_data:
                full_df = pd.concat(combined_data, ignore_index=True)
                full_df.to_parquet(output_file, compression='snappy')

                logger.info(f"💾 Saved {len(data)} tickers to Parquet format")
                logger.info(f"📊 Total records: {len(full_df):,}")
                logger.info(f"💽 File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

        except Exception as e:
            logger.error(f"Failed to save Parquet data: {e}")
            raise

    async def download_historical_data(self, ticker_file: str) -> Dict[str, Any]:
        """Main method to download historical data for all tickers."""
        # Load tickers
        tickers = self._load_tickers(ticker_file)
        if not tickers:
            raise ValueError(f"No tickers found in {ticker_file}")

        # Download all tickers
        all_data = await self.download_all_tickers(tickers)

        # Save data
        if all_data:
            output_file = self.output_dir / "nasdaq_historical_data.parquet"
            self._save_data(all_data, output_file)
            logger.info(f"Saved {len(all_data)} tickers to {output_file}")
        else:
            logger.warning("No data to save")

        return self.download_stats

    def save_data(self, data: Dict[str, pd.DataFrame], filename: str = "nasdaq_3mo.pkl"):
        """Save downloaded data to pickle file."""
        output_file = self.output_dir / filename
        
        try:
            # Convert to multi-level DataFrame for consistency
            if data:
                combined_data = pd.concat(data, axis=1)
                combined_data.to_pickle(output_file)
                
                logger.info(f"Saved {len(data)} tickers to {output_file}")
                logger.info(f"Data shape: {combined_data.shape}")
                logger.info(f"Date range: {combined_data.index.min()} to {combined_data.index.max()}")
                
                return output_file
            else:
                logger.warning("No data to save")
                return None
                
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise
    
    def get_download_summary(self) -> Dict:
        """Get summary of download statistics."""
        duration = None
        if self.download_stats['start_time'] and self.download_stats['end_time']:
            duration = self.download_stats['end_time'] - self.download_stats['start_time']
        
        return {
            **self.download_stats,
            'duration': str(duration) if duration else None,
            'success_rate': (self.download_stats['successful_downloads'] / 
                           max(self.download_stats['total_tickers'], 1)) * 100
        }


async def download_nasdaq_historical_data() -> Dict:
    """Main function to download NASDAQ historical data."""
    downloader = DataDownloader()
    
    # Load ticker list
    tickers = downloader.load_ticker_list()
    
    # Download data
    logger.info(f"Starting download of {len(tickers)} NASDAQ tickers...")
    data = await downloader.download_all_tickers(tickers)
    
    # Save data
    output_file = downloader.save_data(data)
    
    # Get summary
    summary = downloader.get_download_summary()
    
    logger.info("Historical data download completed!")
    logger.info(f"Summary: {summary}")
    
    return {
        'output_file': str(output_file) if output_file else None,
        'ticker_count': len(data),
        'summary': summary
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(download_nasdaq_historical_data())
    print(f"Download complete: {result}")
