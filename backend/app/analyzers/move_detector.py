"""
Move Detection and Event Labeling
Identifies significant +20%/-20% moves in historical data for backtesting.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pickle

logger = logging.getLogger(__name__)


class MoveDetector:
    """Detect significant stock moves for moon/rug pattern analysis."""
    
    def __init__(self, 
                 data_file: str = "data/backtest/nasdaq_3mo.pkl",
                 moon_threshold: float = 20.0,
                 rug_threshold: float = -20.0,
                 max_days: int = 3,
                 min_volume: int = 100000):
        
        self.data_file = Path(data_file)
        self.moon_threshold = moon_threshold
        self.rug_threshold = rug_threshold
        self.max_days = max_days
        self.min_volume = min_volume
        
        self.data = None
        self.moon_events = []
        self.rug_events = []
        
    def load_historical_data(self) -> pd.DataFrame:
        """Load historical OHLCV data from pickle file."""
        try:
            self.data = pd.read_pickle(self.data_file)
            logger.info(f"Loaded historical data: {self.data.shape}")
            logger.info(f"Date range: {self.data.index.min()} to {self.data.index.max()}")
            
            # Get ticker list from columns
            if isinstance(self.data.columns, pd.MultiIndex):
                tickers = self.data.columns.levels[0].tolist()
            else:
                tickers = [col.split('_')[0] for col in self.data.columns if '_Close' in col]
                tickers = list(set(tickers))
            
            logger.info(f"Found {len(tickers)} tickers in dataset")
            return self.data
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            raise
    
    def get_ticker_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Extract OHLCV data for a specific ticker."""
        try:
            if isinstance(self.data.columns, pd.MultiIndex):
                # Multi-level columns from yfinance
                if ticker in self.data.columns.levels[0]:
                    ticker_data = self.data[ticker].copy()
                    # Ensure we have the required columns
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    if all(col in ticker_data.columns for col in required_cols):
                        return ticker_data[required_cols].dropna()
            else:
                # Flat columns - try to reconstruct
                close_col = f"{ticker}_Close"
                if close_col in self.data.columns:
                    ticker_data = pd.DataFrame()
                    for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
                        col_name = f"{ticker}_{col_type}"
                        if col_name in self.data.columns:
                            ticker_data[col_type] = self.data[col_name]
                    
                    if not ticker_data.empty:
                        return ticker_data.dropna()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract data for {ticker}: {e}")
            return None
    
    def detect_moves_for_ticker(self, ticker: str, ticker_data: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Detect moon and rug moves for a single ticker."""
        moon_moves = []
        rug_moves = []
        
        if len(ticker_data) < self.max_days + 1:
            return moon_moves, rug_moves
        
        close_prices = ticker_data['Close']
        volumes = ticker_data['Volume']
        
        # Scan through each potential starting point
        for i in range(len(close_prices) - self.max_days):
            start_date = close_prices.index[i]
            start_price = close_prices.iloc[i]
            start_volume = volumes.iloc[i] if not pd.isna(volumes.iloc[i]) else 0
            
            # Skip if volume is too low
            if start_volume < self.min_volume:
                continue
            
            # Check moves over 1, 2, and 3 days
            for days in range(1, self.max_days + 1):
                if i + days >= len(close_prices):
                    break
                
                end_date = close_prices.index[i + days]
                end_price = close_prices.iloc[i + days]
                
                # Calculate percentage move
                move_pct = ((end_price - start_price) / start_price) * 100
                
                # Check for moon move (>= threshold)
                if move_pct >= self.moon_threshold:
                    # Calculate average volume during the move
                    move_volumes = volumes.iloc[i:i + days + 1]
                    avg_volume = move_volumes.mean() if not move_volumes.isna().all() else 0
                    
                    moon_event = {
                        'ticker': ticker,
                        'start_date': start_date.date(),
                        'end_date': end_date.date(),
                        'days': days,
                        'return_pct': round(move_pct, 2),
                        'start_price': round(start_price, 2),
                        'end_price': round(end_price, 2),
                        'avg_volume': int(avg_volume),
                        'start_volume': int(start_volume)
                    }
                    moon_moves.append(moon_event)
                    break  # Take the first qualifying move from this start point
                
                # Check for rug move (<= threshold)
                elif move_pct <= self.rug_threshold:
                    # Calculate average volume during the move
                    move_volumes = volumes.iloc[i:i + days + 1]
                    avg_volume = move_volumes.mean() if not move_volumes.isna().all() else 0
                    
                    rug_event = {
                        'ticker': ticker,
                        'start_date': start_date.date(),
                        'end_date': end_date.date(),
                        'days': days,
                        'return_pct': round(move_pct, 2),
                        'start_price': round(start_price, 2),
                        'end_price': round(end_price, 2),
                        'avg_volume': int(avg_volume),
                        'start_volume': int(start_volume)
                    }
                    rug_moves.append(rug_event)
                    break  # Take the first qualifying move from this start point
        
        return moon_moves, rug_moves
    
    def detect_all_moves(self) -> Tuple[List[Dict], List[Dict]]:
        """Detect moves for all tickers in the dataset."""
        if self.data is None:
            self.load_historical_data()
        
        all_moon_events = []
        all_rug_events = []
        
        # Get list of tickers
        if isinstance(self.data.columns, pd.MultiIndex):
            tickers = self.data.columns.levels[0].tolist()
        else:
            tickers = list(set([col.split('_')[0] for col in self.data.columns if '_Close' in col]))
        
        logger.info(f"Scanning {len(tickers)} tickers for significant moves...")
        
        processed_count = 0
        for ticker in tickers:
            ticker_data = self.get_ticker_data(ticker)
            
            if ticker_data is not None and len(ticker_data) > self.max_days:
                moon_moves, rug_moves = self.detect_moves_for_ticker(ticker, ticker_data)
                all_moon_events.extend(moon_moves)
                all_rug_events.extend(rug_moves)
                
                if moon_moves or rug_moves:
                    logger.debug(f"{ticker}: {len(moon_moves)} moon, {len(rug_moves)} rug events")
            
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count}/{len(tickers)} tickers...")
        
        self.moon_events = all_moon_events
        self.rug_events = all_rug_events
        
        logger.info(f"Move detection complete:")
        logger.info(f"  Moon events: {len(all_moon_events)}")
        logger.info(f"  Rug events: {len(all_rug_events)}")
        
        return all_moon_events, all_rug_events
    
    def filter_high_confidence_events(self, events: List[Dict], min_move_pct: float = 25.0) -> List[Dict]:
        """Filter events for high-confidence moves (>25% for manual validation)."""
        high_confidence = [
            event for event in events 
            if abs(event['return_pct']) >= min_move_pct
        ]
        
        logger.info(f"High-confidence events (>={min_move_pct}%): {len(high_confidence)}")
        return high_confidence
    
    def save_events(self, output_dir: str = "data/backtest"):
        """Save detected events to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save moon events
        if self.moon_events:
            moon_df = pd.DataFrame(self.moon_events)
            moon_file = output_path / "moon_events.csv"
            moon_df.to_csv(moon_file, index=False)
            logger.info(f"Saved {len(self.moon_events)} moon events to {moon_file}")
            
            # Save high-confidence moon events
            high_conf_moon = self.filter_high_confidence_events(self.moon_events)
            if high_conf_moon:
                high_conf_moon_df = pd.DataFrame(high_conf_moon)
                high_conf_file = output_path / "moon_events_high_confidence.csv"
                high_conf_moon_df.to_csv(high_conf_file, index=False)
                logger.info(f"Saved {len(high_conf_moon)} high-confidence moon events to {high_conf_file}")
        
        # Save rug events
        if self.rug_events:
            rug_df = pd.DataFrame(self.rug_events)
            rug_file = output_path / "rug_events.csv"
            rug_df.to_csv(rug_file, index=False)
            logger.info(f"Saved {len(self.rug_events)} rug events to {rug_file}")
            
            # Save high-confidence rug events
            high_conf_rug = self.filter_high_confidence_events(self.rug_events)
            if high_conf_rug:
                high_conf_rug_df = pd.DataFrame(high_conf_rug)
                high_conf_file = output_path / "rug_events_high_confidence.csv"
                high_conf_rug_df.to_csv(high_conf_file, index=False)
                logger.info(f"Saved {len(high_conf_rug)} high-confidence rug events to {high_conf_file}")
        
        return {
            'moon_events': len(self.moon_events),
            'rug_events': len(self.rug_events),
            'high_conf_moon': len(self.filter_high_confidence_events(self.moon_events)),
            'high_conf_rug': len(self.filter_high_confidence_events(self.rug_events))
        }
    
    def get_event_statistics(self) -> Dict:
        """Get statistics about detected events."""
        stats = {
            'total_moon_events': len(self.moon_events),
            'total_rug_events': len(self.rug_events),
            'total_events': len(self.moon_events) + len(self.rug_events)
        }
        
        if self.moon_events:
            moon_df = pd.DataFrame(self.moon_events)
            stats['moon_stats'] = {
                'avg_return': moon_df['return_pct'].mean(),
                'max_return': moon_df['return_pct'].max(),
                'avg_days': moon_df['days'].mean(),
                'day_distribution': moon_df['days'].value_counts().to_dict()
            }
        
        if self.rug_events:
            rug_df = pd.DataFrame(self.rug_events)
            stats['rug_stats'] = {
                'avg_return': rug_df['return_pct'].mean(),
                'min_return': rug_df['return_pct'].min(),
                'avg_days': rug_df['days'].mean(),
                'day_distribution': rug_df['days'].value_counts().to_dict()
            }
        
        return stats


async def detect_nasdaq_moves() -> Dict:
    """Main function to detect moon and rug moves in NASDAQ data."""
    detector = MoveDetector()
    
    # Load data and detect moves
    detector.load_historical_data()
    moon_events, rug_events = detector.detect_all_moves()
    
    # Save events
    save_stats = detector.save_events()
    
    # Get statistics
    event_stats = detector.get_event_statistics()
    
    logger.info("Move detection completed successfully!")
    logger.info(f"Event statistics: {event_stats}")
    
    return {
        'save_stats': save_stats,
        'event_stats': event_stats,
        'moon_events': len(moon_events),
        'rug_events': len(rug_events)
    }


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(detect_nasdaq_moves())
    print(f"Move detection complete: {result}")
