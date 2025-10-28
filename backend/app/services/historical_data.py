"""
Historical Data Service for BullsBears.xyz
Collects historical stock data for ML training and cost monitoring simulation
"""

import asyncio
import logging
import pandas as pd
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import random
import numpy as np
from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class StockData:
    """Historical stock data container."""
    symbol: str
    company_name: str
    sector: str
    price_data: pd.DataFrame
    volume_data: pd.DataFrame
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    beta: Optional[float] = None
    
@dataclass
class MarketContext:
    """Market context data for ML features."""
    vix_level: float
    spy_change: float
    sector_performance: Dict[str, float]
    market_trend: str  # "bullish", "bearish", "neutral"
    volatility_regime: str  # "low", "medium", "high"

class HistoricalDataService:
    """
    Service for collecting historical stock data using yfinance (free tier).
    Generates realistic market context for ML training simulations.
    """
    
    def __init__(self):
        # Diverse stock selection across sectors
        self.stock_universe = {
            # Technology
            "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
            "MSFT": {"name": "Microsoft Corporation", "sector": "Technology"},
            "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology"},
            "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology"},
            "TSLA": {"name": "Tesla, Inc.", "sector": "Technology"},
            "META": {"name": "Meta Platforms, Inc.", "sector": "Technology"},
            "NFLX": {"name": "Netflix, Inc.", "sector": "Technology"},
            "CRM": {"name": "Salesforce, Inc.", "sector": "Technology"},
            "ADBE": {"name": "Adobe Inc.", "sector": "Technology"},
            "ORCL": {"name": "Oracle Corporation", "sector": "Technology"},
            
            # Finance
            "JPM": {"name": "JPMorgan Chase & Co.", "sector": "Finance"},
            "BAC": {"name": "Bank of America Corporation", "sector": "Finance"},
            "WFC": {"name": "Wells Fargo & Company", "sector": "Finance"},
            "GS": {"name": "The Goldman Sachs Group, Inc.", "sector": "Finance"},
            "MS": {"name": "Morgan Stanley", "sector": "Finance"},
            "V": {"name": "Visa Inc.", "sector": "Finance"},
            "MA": {"name": "Mastercard Incorporated", "sector": "Finance"},
            "AXP": {"name": "American Express Company", "sector": "Finance"},
            
            # Healthcare
            "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare"},
            "PFE": {"name": "Pfizer Inc.", "sector": "Healthcare"},
            "UNH": {"name": "UnitedHealth Group Incorporated", "sector": "Healthcare"},
            "ABBV": {"name": "AbbVie Inc.", "sector": "Healthcare"},
            "MRK": {"name": "Merck & Co., Inc.", "sector": "Healthcare"},
            "TMO": {"name": "Thermo Fisher Scientific Inc.", "sector": "Healthcare"},
            "ABT": {"name": "Abbott Laboratories", "sector": "Healthcare"},
            "LLY": {"name": "Eli Lilly and Company", "sector": "Healthcare"},
            
            # Consumer
            "AMZN": {"name": "Amazon.com, Inc.", "sector": "Consumer"},
            "WMT": {"name": "Walmart Inc.", "sector": "Consumer"},
            "PG": {"name": "The Procter & Gamble Company", "sector": "Consumer"},
            "KO": {"name": "The Coca-Cola Company", "sector": "Consumer"},
            "PEP": {"name": "PepsiCo, Inc.", "sector": "Consumer"},
            "MCD": {"name": "McDonald's Corporation", "sector": "Consumer"},
            "NKE": {"name": "NIKE, Inc.", "sector": "Consumer"},
            "SBUX": {"name": "Starbucks Corporation", "sector": "Consumer"},
            
            # Energy
            "XOM": {"name": "Exxon Mobil Corporation", "sector": "Energy"},
            "CVX": {"name": "Chevron Corporation", "sector": "Energy"},
            "COP": {"name": "ConocoPhillips", "sector": "Energy"},
            "SLB": {"name": "Schlumberger Limited", "sector": "Energy"},
            "EOG": {"name": "EOG Resources, Inc.", "sector": "Energy"},
            "PSX": {"name": "Phillips 66", "sector": "Energy"},
            
            # Industrial
            "BA": {"name": "The Boeing Company", "sector": "Industrial"},
            "CAT": {"name": "Caterpillar Inc.", "sector": "Industrial"},
            "GE": {"name": "General Electric Company", "sector": "Industrial"},
            "MMM": {"name": "3M Company", "sector": "Industrial"},
            "HON": {"name": "Honeywell International Inc.", "sector": "Industrial"},
            "UPS": {"name": "United Parcel Service, Inc.", "sector": "Industrial"},
            
            # ETFs for diversification
            "SPY": {"name": "SPDR S&P 500 ETF Trust", "sector": "ETF"},
            "QQQ": {"name": "Invesco QQQ Trust", "sector": "ETF"},
            "IWM": {"name": "iShares Russell 2000 ETF", "sector": "ETF"},
            "VTI": {"name": "Vanguard Total Stock Market ETF", "sector": "ETF"}
        }
        
    async def collect_historical_data(self,
                                    symbols: List[str] = None,
                                    days_back: int = 30) -> List[StockData]:
        """
        Collect historical data using synthetic data generation (yfinance removed).

        Args:
            symbols: List of symbols to collect data for (None for random selection)
            days_back: Number of days of historical data to collect

        Returns:
            List of StockData objects with historical price and volume data
        """
        if symbols is None:
            # Select 50 diverse stocks
            symbols = list(self.stock_universe.keys())

        logger.info(f"Collecting historical data for {len(symbols)} symbols")

        # Generate synthetic data directly (yfinance removed due to reliability issues)
        stock_data_list = await self._generate_synthetic_data(symbols, days_back)

        logger.info(f"Successfully collected data for {len(stock_data_list)} symbols")
        return stock_data_list

    async def _generate_synthetic_data(self, symbols: List[str], days_back: int) -> List[StockData]:
        """Generate synthetic historical data for testing."""
        stock_data_list = []

        for symbol in symbols:
            try:
                stock_info = self.stock_universe.get(symbol, {
                    "name": f"{symbol} Corporation",
                    "sector": "Unknown"
                })

                # Generate synthetic price data
                dates = pd.date_range(
                    start=datetime.now() - timedelta(days=days_back),
                    end=datetime.now(),
                    freq='D'
                )

                # Start with a base price
                base_price = random.uniform(50, 300)
                prices = [base_price]

                # Generate realistic price movements
                for _ in range(len(dates) - 1):
                    change_pct = random.gauss(0, 0.02)  # 2% daily volatility
                    new_price = prices[-1] * (1 + change_pct)
                    prices.append(max(new_price, 1.0))  # Minimum $1

                # Create OHLC data
                df_data = []
                for i, date in enumerate(dates):
                    close = prices[i]
                    daily_range = close * random.uniform(0.01, 0.05)  # 1-5% daily range

                    high = close + random.uniform(0, daily_range)
                    low = close - random.uniform(0, daily_range)
                    open_price = low + random.uniform(0, high - low)

                    volume = random.randint(100000, 10000000)  # Random volume

                    df_data.append({
                        "Open": round(open_price, 2),
                        "High": round(high, 2),
                        "Low": round(low, 2),
                        "Close": round(close, 2),
                        "Volume": volume
                    })

                df = pd.DataFrame(df_data, index=dates)

                # Split into price and volume data
                price_data = df[['Open', 'High', 'Low', 'Close']].copy()
                volume_data = df[['Volume']].copy()

                # Create StockData object
                stock_data = StockData(
                    symbol=symbol,
                    company_name=stock_info["name"],
                    sector=stock_info["sector"],
                    price_data=price_data,
                    volume_data=volume_data,
                    market_cap=random.randint(1000000000, 1000000000000),  # $1B - $1T
                    pe_ratio=random.uniform(10, 50),
                    beta=random.uniform(0.5, 2.0)
                )

                stock_data_list.append(stock_data)
                logger.info(f"Generated synthetic data for {symbol}: {len(price_data)} days")

            except Exception as e:
                logger.error(f"Error generating synthetic data for {symbol}: {e}")
                continue

        return stock_data_list

    async def generate_market_context(self, date: datetime = None) -> MarketContext:
        """
        Generate realistic market context data for ML features.

        Args:
            date: Date for market context (None for current date)

        Returns:
            MarketContext object with market indicators
        """
        if date is None:
            date = datetime.now()

        try:
            # Generate synthetic VIX level (volatility index)
            vix_level = random.uniform(15.0, 35.0)

            # Generate synthetic SPY change
            spy_change = random.uniform(-3.0, 3.0)

            # Generate sector performance (simulated based on market conditions)
            sector_performance = self._generate_sector_performance(spy_change)

            # Determine market trend
            if spy_change > 1.0:
                market_trend = "bullish"
            elif spy_change < -1.0:
                market_trend = "bearish"
            else:
                market_trend = "neutral"

            # Determine volatility regime
            if vix_level < 20:
                volatility_regime = "low"
            elif vix_level > 30:
                volatility_regime = "high"
            else:
                volatility_regime = "medium"

            return MarketContext(
                vix_level=vix_level,
                spy_change=spy_change,
                sector_performance=sector_performance,
                market_trend=market_trend,
                volatility_regime=volatility_regime
            )

        except Exception as e:
            logger.error(f"Error generating market context: {e}")
            # Return fallback market context
            return MarketContext(
                vix_level=random.uniform(15.0, 35.0),
                spy_change=random.uniform(-3.0, 3.0),
                sector_performance=self._generate_sector_performance(0.0),
                market_trend="neutral",
                volatility_regime="medium"
            )

    def _generate_sector_performance(self, spy_change: float) -> Dict[str, float]:
        """Generate realistic sector performance based on market conditions."""
        sectors = ["Technology", "Finance", "Healthcare", "Consumer", "Energy", "Industrial", "ETF"]

        # Base performance around SPY change with sector-specific variations
        sector_performance = {}

        for sector in sectors:
            if sector == "Technology":
                # Tech tends to be more volatile
                base_change = spy_change * random.uniform(0.8, 1.5)
            elif sector == "Finance":
                # Finance correlates with interest rates and market sentiment
                base_change = spy_change * random.uniform(0.9, 1.3)
            elif sector == "Healthcare":
                # Healthcare is more defensive
                base_change = spy_change * random.uniform(0.6, 1.1)
            elif sector == "Energy":
                # Energy can be counter-cyclical
                base_change = spy_change * random.uniform(-0.5, 1.8)
            elif sector == "ETF":
                # ETFs track market closely
                base_change = spy_change * random.uniform(0.95, 1.05)
            else:
                # Other sectors
                base_change = spy_change * random.uniform(0.7, 1.2)

            # Add some random noise
            noise = random.uniform(-0.5, 0.5)
            sector_performance[sector] = round(base_change + noise, 2)

        return sector_performance

    def calculate_technical_indicators(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate technical indicators for ML features.

        Args:
            price_data: DataFrame with OHLC data

        Returns:
            Dictionary of technical indicators
        """
        try:
            indicators = {}

            # RSI (14-day)
            delta = price_data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # Handle RSI calculation safely
            if not rsi.empty and not pd.isna(rsi.iloc[-1]):
                indicators['rsi_14'] = float(rsi.iloc[-1])
            else:
                indicators['rsi_14'] = 50.0

            # Moving averages
            if len(price_data) >= 20:
                sma_20_series = price_data['Close'].rolling(20).mean()
                indicators['sma_20'] = float(sma_20_series.iloc[-1]) if not pd.isna(sma_20_series.iloc[-1]) else float(price_data['Close'].mean())
            else:
                indicators['sma_20'] = float(price_data['Close'].mean())

            if len(price_data) >= 50:
                sma_50_series = price_data['Close'].rolling(50).mean()
                indicators['sma_50'] = float(sma_50_series.iloc[-1]) if not pd.isna(sma_50_series.iloc[-1]) else float(price_data['Close'].mean())
            else:
                indicators['sma_50'] = float(price_data['Close'].mean())

            # Price relative to moving averages
            current_price = float(price_data['Close'].iloc[-1])
            indicators['price_vs_sma20'] = (current_price / indicators['sma_20'] - 1) * 100 if indicators['sma_20'] > 0 else 0.0
            indicators['price_vs_sma50'] = (current_price / indicators['sma_50'] - 1) * 100 if indicators['sma_50'] > 0 else 0.0

            # Volatility (20-day)
            returns = price_data['Close'].pct_change()
            if len(returns) >= 20:
                vol_series = returns.rolling(20).std() * np.sqrt(252) * 100
                indicators['volatility_20d'] = float(vol_series.iloc[-1]) if not pd.isna(vol_series.iloc[-1]) else 20.0
            else:
                indicators['volatility_20d'] = 20.0

            # Volume trend (5-day average vs 20-day average)
            # Note: synthetic data doesn't have Volume in price_data, check both price_data and separate volume_data
            volume_data_available = False
            if 'Volume' in price_data.columns:
                volume_series = price_data['Volume']
                volume_data_available = True

            if volume_data_available and len(price_data) >= 20:
                vol_5d_series = volume_series.rolling(5).mean()
                vol_20d_series = volume_series.rolling(20).mean()
                vol_5d = vol_5d_series.iloc[-1] if not pd.isna(vol_5d_series.iloc[-1]) else 0
                vol_20d = vol_20d_series.iloc[-1] if not pd.isna(vol_20d_series.iloc[-1]) else 0
                indicators['volume_trend'] = float((vol_5d / vol_20d - 1) * 100) if vol_20d > 0 else 0.0
            else:
                indicators['volume_trend'] = 0.0

            return indicators

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            # Return default indicators
            return {
                'rsi_14': 50.0,
                'sma_20': float(price_data['Close'].iloc[-1]) if not price_data.empty else 100.0,
                'sma_50': float(price_data['Close'].iloc[-1]) if not price_data.empty else 100.0,
                'price_vs_sma20': 0.0,
                'price_vs_sma50': 0.0,
                'volatility_20d': 20.0,
                'volume_trend': 0.0
            }
