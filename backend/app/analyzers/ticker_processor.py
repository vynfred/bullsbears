"""
NASDAQ Ticker Processing for Historical Data Collection
Processes the NASDAQ screener CSV and creates clean ticker lists for backtesting.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Set
import re

logger = logging.getLogger(__name__)


class TickerProcessor:
    """Process NASDAQ ticker data and create filtered lists for backtesting."""
    
    def __init__(self, csv_path: str = "../Data/nasdaq_screener_1762100638908.csv"):
        self.csv_path = Path(csv_path)
        self.df = None
        self.filtered_tickers = []
        
    def load_nasdaq_data(self) -> pd.DataFrame:
        """Load NASDAQ screener CSV data."""
        try:
            self.df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded {len(self.df)} tickers from NASDAQ screener")
            return self.df
        except Exception as e:
            logger.error(f"Failed to load NASDAQ data: {e}")
            raise
    
    def filter_valid_tickers(self) -> List[str]:
        """Filter out invalid tickers and focus on liquid, tradeable stocks."""
        if self.df is None:
            self.load_nasdaq_data()
        
        # Start with all symbols
        filtered = self.df.copy()
        initial_count = len(filtered)
        
        # Remove invalid symbols
        filtered = filtered.dropna(subset=['Symbol'])
        logger.info(f"After removing NaN symbols: {len(filtered)} (removed {initial_count - len(filtered)})")
        
        # Remove SPACs, warrants, units, and other derivatives
        spac_patterns = [
            r'[A-Z]+U$',  # Units (ends with U)
            r'[A-Z]+W$',  # Warrants (ends with W)  
            r'[A-Z]+R$',  # Rights (ends with R)
            r'[A-Z]+\+$', # Preferred shares
            r'[A-Z]+\.$', # Class shares with dots
        ]
        
        for pattern in spac_patterns:
            before_count = len(filtered)
            filtered = filtered[~filtered['Symbol'].str.match(pattern, na=False)]
            removed = before_count - len(filtered)
            if removed > 0:
                logger.info(f"Removed {removed} tickers matching pattern {pattern}")
        
        # Remove tickers with special characters (except hyphens for some valid tickers)
        before_count = len(filtered)
        filtered = filtered[~filtered['Symbol'].str.contains(r'[^A-Z\-]', na=False)]
        removed = before_count - len(filtered)
        if removed > 0:
            logger.info(f"Removed {removed} tickers with special characters")
        
        # Filter by market cap (remove micro-caps < $100M)
        if 'Market Cap' in filtered.columns:
            before_count = len(filtered)
            # Convert market cap to numeric, handling string formats
            filtered['Market Cap Numeric'] = pd.to_numeric(filtered['Market Cap'], errors='coerce')
            filtered = filtered[
                (filtered['Market Cap Numeric'].isna()) |  # Keep NaN (unknown market cap)
                (filtered['Market Cap Numeric'] >= 100_000_000)  # Keep >= $100M
            ]
            removed = before_count - len(filtered)
            if removed > 0:
                logger.info(f"Removed {removed} micro-cap stocks (< $100M market cap)")
        
        # Filter by volume (remove low-volume stocks)
        if 'Volume' in filtered.columns:
            before_count = len(filtered)
            filtered['Volume Numeric'] = pd.to_numeric(filtered['Volume'], errors='coerce')
            # Keep stocks with >100K average volume or unknown volume
            filtered = filtered[
                (filtered['Volume Numeric'].isna()) |  # Keep NaN (unknown volume)
                (filtered['Volume Numeric'] >= 100_000)  # Keep >= 100K volume
            ]
            removed = before_count - len(filtered)
            if removed > 0:
                logger.info(f"Removed {removed} low-volume stocks (< 100K volume)")
        
        # Extract clean ticker list
        self.filtered_tickers = filtered['Symbol'].str.strip().tolist()
        
        logger.info(f"Final filtered ticker count: {len(self.filtered_tickers)}")
        logger.info(f"Removed {initial_count - len(self.filtered_tickers)} invalid/illiquid tickers")
        
        return self.filtered_tickers
    
    def get_priority_tickers(self, limit: int = 1000) -> List[str]:
        """Get priority tickers focusing on volatile sectors for backtesting."""
        if not self.filtered_tickers:
            self.filter_valid_tickers()
        
        if self.df is None:
            return self.filtered_tickers[:limit]
        
        priority_tickers = []
        
        # Define high-priority sectors and keywords
        volatile_sectors = [
            'Technology', 'Biotechnology', 'Pharmaceuticals', 'Energy', 
            'Consumer Discretionary', 'Communication Services'
        ]
        
        meme_keywords = [
            'gaming', 'electric', 'crypto', 'blockchain', 'cannabis', 'solar',
            'battery', 'autonomous', 'ai', 'artificial intelligence', 'cloud'
        ]
        
        # Get tickers from volatile sectors
        if 'Sector' in self.df.columns:
            sector_tickers = self.df[
                self.df['Sector'].isin(volatile_sectors) & 
                self.df['Symbol'].isin(self.filtered_tickers)
            ]['Symbol'].tolist()
            priority_tickers.extend(sector_tickers)
            logger.info(f"Added {len(sector_tickers)} tickers from volatile sectors")
        
        # Get tickers with meme/volatile keywords in name or industry
        if 'Name' in self.df.columns:
            name_pattern = '|'.join(meme_keywords)
            keyword_tickers = self.df[
                (self.df['Name'].str.contains(name_pattern, case=False, na=False) |
                 self.df.get('Industry', pd.Series()).str.contains(name_pattern, case=False, na=False)) &
                self.df['Symbol'].isin(self.filtered_tickers)
            ]['Symbol'].tolist()
            priority_tickers.extend(keyword_tickers)
            logger.info(f"Added {len(keyword_tickers)} tickers with volatile keywords")
        
        # Add well-known volatile tickers manually
        manual_priority = [
            'TSLA', 'GME', 'AMC', 'NVDA', 'AMD', 'PLTR', 'HOOD', 'COIN',
            'RIVN', 'LCID', 'SPCE', 'ARKK', 'SOXL', 'TQQQ', 'SQQQ',
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'CRM',
            'SMCI', 'AVGO', 'INTC', 'QCOM', 'ADBE', 'NOW', 'SNOW'
        ]
        
        manual_available = [t for t in manual_priority if t in self.filtered_tickers]
        priority_tickers.extend(manual_available)
        logger.info(f"Added {len(manual_available)} manually selected priority tickers")
        
        # Remove duplicates and limit
        priority_tickers = list(dict.fromkeys(priority_tickers))  # Preserve order, remove dupes
        
        # Fill remaining slots with highest market cap tickers
        remaining_slots = limit - len(priority_tickers)
        if remaining_slots > 0 and 'Market Cap' in self.df.columns:
            remaining_df = self.df[
                (~self.df['Symbol'].isin(priority_tickers)) &
                (self.df['Symbol'].isin(self.filtered_tickers))
            ].copy()
            
            remaining_df['Market Cap Numeric'] = pd.to_numeric(remaining_df['Market Cap'], errors='coerce')
            top_remaining = remaining_df.nlargest(remaining_slots, 'Market Cap Numeric')['Symbol'].tolist()
            priority_tickers.extend(top_remaining)
            logger.info(f"Added {len(top_remaining)} high market cap tickers to fill remaining slots")
        
        final_list = priority_tickers[:limit]
        logger.info(f"Final priority ticker list: {len(final_list)} tickers")
        
        return final_list
    
    def save_ticker_lists(self, output_dir: str = "data/backtest"):
        """Save processed ticker lists to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save all filtered tickers
        all_tickers_file = output_path / "nasdaq_filtered_tickers.txt"
        with open(all_tickers_file, 'w') as f:
            f.write('\n'.join(self.filtered_tickers))
        logger.info(f"Saved {len(self.filtered_tickers)} filtered tickers to {all_tickers_file}")
        
        # Save priority tickers
        priority_tickers = self.get_priority_tickers(1000)
        priority_file = output_path / "nasdaq_priority_tickers.txt"
        with open(priority_file, 'w') as f:
            f.write('\n'.join(priority_tickers))
        logger.info(f"Saved {len(priority_tickers)} priority tickers to {priority_file}")
        
        # Save ticker metadata
        if self.df is not None:
            metadata_df = self.df[self.df['Symbol'].isin(priority_tickers)].copy()
            metadata_file = output_path / "nasdaq_ticker_metadata.csv"
            metadata_df.to_csv(metadata_file, index=False)
            logger.info(f"Saved ticker metadata to {metadata_file}")
        
        return {
            'all_tickers': all_tickers_file,
            'priority_tickers': priority_file,
            'metadata': metadata_file if self.df is not None else None
        }
    
    def get_ticker_stats(self) -> Dict:
        """Get statistics about the processed tickers."""
        if not self.filtered_tickers:
            self.filter_valid_tickers()
        
        stats = {
            'total_filtered': len(self.filtered_tickers),
            'priority_count': len(self.get_priority_tickers(1000))
        }
        
        if self.df is not None:
            filtered_df = self.df[self.df['Symbol'].isin(self.filtered_tickers)]
            
            # Sector distribution
            if 'Sector' in filtered_df.columns:
                stats['sectors'] = filtered_df['Sector'].value_counts().to_dict()
            
            # Market cap distribution
            if 'Market Cap' in filtered_df.columns:
                filtered_df['Market Cap Numeric'] = pd.to_numeric(filtered_df['Market Cap'], errors='coerce')
                stats['market_cap_ranges'] = {
                    'mega_cap_10B+': len(filtered_df[filtered_df['Market Cap Numeric'] >= 10_000_000_000]),
                    'large_cap_2B_10B': len(filtered_df[
                        (filtered_df['Market Cap Numeric'] >= 2_000_000_000) & 
                        (filtered_df['Market Cap Numeric'] < 10_000_000_000)
                    ]),
                    'mid_cap_300M_2B': len(filtered_df[
                        (filtered_df['Market Cap Numeric'] >= 300_000_000) & 
                        (filtered_df['Market Cap Numeric'] < 2_000_000_000)
                    ]),
                    'small_cap_100M_300M': len(filtered_df[
                        (filtered_df['Market Cap Numeric'] >= 100_000_000) & 
                        (filtered_df['Market Cap Numeric'] < 300_000_000)
                    ])
                }
        
        return stats


async def process_nasdaq_tickers() -> Dict:
    """Main function to process NASDAQ tickers for backtesting."""
    processor = TickerProcessor()
    
    # Load and filter tickers
    processor.load_nasdaq_data()
    filtered_tickers = processor.filter_valid_tickers()
    
    # Save ticker lists
    saved_files = processor.save_ticker_lists()
    
    # Get statistics
    stats = processor.get_ticker_stats()
    
    logger.info("NASDAQ ticker processing completed successfully")
    logger.info(f"Statistics: {stats}")
    
    return {
        'filtered_count': len(filtered_tickers),
        'priority_count': stats['priority_count'],
        'saved_files': saved_files,
        'stats': stats
    }


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(process_nasdaq_tickers())
    print(f"Processing complete: {result}")
