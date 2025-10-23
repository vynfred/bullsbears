"""
Stock Data Service - Primary: Alpha Vantage, Backup: Yahoo Finance
Handles real-time quotes, historical data, and options chains with caching and rate limiting.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import yfinance as yf
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.redis_client import redis_client
from ..models.stock import Stock, StockPrice
from ..models.options_data import OptionsData, OptionsChain

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for Alpha Vantage API (5 calls/minute free tier)."""
    
    def __init__(self, max_calls: int = 5, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = datetime.now()
        # Remove calls older than time window
        self.calls = [call_time for call_time in self.calls 
                     if (now - call_time).seconds < self.time_window]
        
        if len(self.calls) >= self.max_calls:
            # Wait until oldest call expires
            wait_time = self.time_window - (now - self.calls[0]).seconds + 1
            logger.info(f"Rate limit reached, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
            self.calls = self.calls[1:]  # Remove oldest call
        
        self.calls.append(now)


class StockDataService:
    """
    Stock data service with Alpha Vantage primary and yfinance backup.
    Implements caching, rate limiting, and error handling.
    """
    
    def __init__(self):
        self.alpha_vantage_key = settings.alpha_vantage_api_key
        self.rate_limiter = RateLimiter()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_real_time_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote with 30-second caching.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Dict with price data or None if failed
        """
        cache_key = f"quote:{symbol}"
        
        # Check cache first
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for quote {symbol}")
            return cached_data
        
        # Try Alpha Vantage first
        try:
            quote_data = await self._fetch_alpha_vantage_quote(symbol)
            if quote_data:
                # Cache for 30 seconds
                await redis_client.cache_with_ttl(cache_key, quote_data, settings.cache_api_responses)
                return quote_data
        except Exception as e:
            logger.error(f"Alpha Vantage quote failed for {symbol}: {e}")
        
        # Fallback to yfinance
        try:
            quote_data = await self._fetch_yfinance_quote(symbol)
            if quote_data:
                # Cache for 30 seconds
                await redis_client.cache_with_ttl(cache_key, quote_data, settings.cache_api_responses)
                return quote_data
        except Exception as e:
            logger.error(f"yfinance quote failed for {symbol}: {e}")
        
        logger.error(f"All quote sources failed for {symbol}")
        return None
    
    async def _fetch_alpha_vantage_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time quote from Alpha Vantage."""
        await self.rate_limiter.wait_if_needed()
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.alpha_vantage_key
        }
        
        session = await self._get_session()
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            
            data = await response.json()
            
            if "Error Message" in data:
                raise Exception(data["Error Message"])
            
            if "Note" in data:
                raise Exception("API rate limit exceeded")
            
            quote = data.get("Global Quote", {})
            if not quote:
                raise Exception("No quote data returned")
            
            return {
                "symbol": symbol,
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                "volume": int(quote.get("06. volume", 0)),
                "open": float(quote.get("02. open", 0)),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
                "previous_close": float(quote.get("08. previous close", 0)),
                "timestamp": datetime.now(),
                "source": "alpha_vantage"
            }
    
    async def _fetch_yfinance_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time quote from yfinance (backup)."""
        def _get_yf_data():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            if hist.empty:
                raise Exception("No historical data available")
            
            latest = hist.iloc[-1]
            
            return {
                "symbol": symbol,
                "price": float(latest["Close"]),
                "change": float(latest["Close"] - latest["Open"]),
                "change_percent": f"{((latest['Close'] - latest['Open']) / latest['Open'] * 100):.2f}",
                "volume": int(latest["Volume"]),
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "previous_close": float(latest["Open"]),  # Approximation
                "timestamp": datetime.now(),
                "source": "yfinance"
            }
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_yf_data)

    async def get_historical_data(self, symbol: str, period: str = "1y") -> Optional[List[Dict[str, Any]]]:
        """
        Get historical price data with caching.

        Args:
            symbol: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            List of historical price data
        """
        cache_key = f"historical:{symbol}:{period}"

        # Check cache (24 hour TTL for historical data)
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for historical {symbol}:{period}")
            return cached_data

        # Try Alpha Vantage first
        try:
            historical_data = await self._fetch_alpha_vantage_historical(symbol, period)
            if historical_data:
                await redis_client.cache_with_ttl(cache_key, historical_data, settings.cache_historical_data)
                return historical_data
        except Exception as e:
            logger.error(f"Alpha Vantage historical failed for {symbol}: {e}")

        # Fallback to yfinance
        try:
            historical_data = await self._fetch_yfinance_historical(symbol, period)
            if historical_data:
                await redis_client.cache_with_ttl(cache_key, historical_data, settings.cache_historical_data)
                return historical_data
        except Exception as e:
            logger.error(f"yfinance historical failed for {symbol}: {e}")

        return None

    async def _fetch_alpha_vantage_historical(self, symbol: str, period: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical data from Alpha Vantage."""
        await self.rate_limiter.wait_if_needed()

        # Map period to Alpha Vantage function
        if period in ["1d", "5d"]:
            function = "TIME_SERIES_INTRADAY"
            interval = "60min"
        else:
            function = "TIME_SERIES_DAILY"
            interval = None

        url = "https://www.alphavantage.co/query"
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.alpha_vantage_key,
            "outputsize": "full"
        }

        if interval:
            params["interval"] = interval

        session = await self._get_session()
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            data = await response.json()

            if "Error Message" in data:
                raise Exception(data["Error Message"])

            # Parse time series data
            time_series_key = None
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break

            if not time_series_key:
                raise Exception("No time series data found")

            time_series = data[time_series_key]
            historical_data = []

            for date_str, values in time_series.items():
                historical_data.append({
                    "date": date_str,
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0))
                })

            # Sort by date (newest first)
            historical_data.sort(key=lambda x: x["date"], reverse=True)

            # Limit based on period
            period_limits = {
                "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
                "6mo": 180, "1y": 365, "2y": 730
            }

            limit = period_limits.get(period, 365)
            return historical_data[:limit]

    async def _fetch_yfinance_historical(self, symbol: str, period: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical data from yfinance."""
        def _get_yf_historical():
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                raise Exception("No historical data available")

            historical_data = []
            for date, row in hist.iterrows():
                historical_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"])
                })

            # Sort by date (newest first)
            historical_data.sort(key=lambda x: x["date"], reverse=True)
            return historical_data

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_yf_historical)

    async def get_options_chain(self, symbol: str, expiration_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get options chain data with caching.

        Args:
            symbol: Stock symbol
            expiration_date: Specific expiration date (YYYY-MM-DD) or None for all

        Returns:
            Options chain data with calls and puts
        """
        cache_key = f"options:{symbol}:{expiration_date or 'all'}"

        # Check cache (5 minute TTL for options data)
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for options {symbol}")
            return cached_data

        # Currently only yfinance supports options (Alpha Vantage requires premium)
        try:
            options_data = await self._fetch_yfinance_options(symbol, expiration_date)
            if options_data:
                await redis_client.cache_with_ttl(cache_key, options_data, settings.cache_indicators)
                return options_data
        except Exception as e:
            logger.error(f"yfinance options failed for {symbol}: {e}")

        return None

    async def _fetch_yfinance_options(self, symbol: str, expiration_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch options chain from yfinance."""
        def _get_yf_options():
            ticker = yf.Ticker(symbol)

            # Get available expiration dates
            expirations = ticker.options
            if not expirations:
                raise Exception("No options data available")

            if expiration_date and expiration_date not in expirations:
                raise Exception(f"Expiration date {expiration_date} not available")

            target_expiration = expiration_date or expirations[0]

            # Get options chain for the expiration
            opt_chain = ticker.option_chain(target_expiration)

            calls_data = []
            puts_data = []

            # Process calls
            for _, call in opt_chain.calls.iterrows():
                calls_data.append({
                    "strike": float(call["strike"]),
                    "last_price": float(call.get("lastPrice", 0)),
                    "bid": float(call.get("bid", 0)),
                    "ask": float(call.get("ask", 0)),
                    "volume": int(call.get("volume", 0)),
                    "open_interest": int(call.get("openInterest", 0)),
                    "implied_volatility": float(call.get("impliedVolatility", 0)),
                    "contract_symbol": call.get("contractSymbol", ""),
                    "option_type": "CALL"
                })

            # Process puts
            for _, put in opt_chain.puts.iterrows():
                puts_data.append({
                    "strike": float(put["strike"]),
                    "last_price": float(put.get("lastPrice", 0)),
                    "bid": float(put.get("bid", 0)),
                    "ask": float(put.get("ask", 0)),
                    "volume": int(put.get("volume", 0)),
                    "open_interest": int(put.get("openInterest", 0)),
                    "implied_volatility": float(put.get("impliedVolatility", 0)),
                    "contract_symbol": put.get("contractSymbol", ""),
                    "option_type": "PUT"
                })

            return {
                "symbol": symbol,
                "expiration_date": target_expiration,
                "available_expirations": list(expirations),
                "calls": calls_data,
                "puts": puts_data,
                "timestamp": datetime.now().isoformat(),
                "source": "yfinance"
            }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_yf_options)

    async def store_stock_data(self, db: Session, symbol: str, quote_data: Dict[str, Any]) -> Stock:
        """Store stock data in database."""
        # Get or create stock record
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            stock = Stock(
                symbol=symbol,
                name=symbol,  # Will be updated with company name later
                exchange="UNKNOWN"
            )
            db.add(stock)
            db.commit()
            db.refresh(stock)

        # Create price record
        price_record = StockPrice(
            stock_id=stock.id,
            timestamp=quote_data["timestamp"],
            open_price=quote_data["open"],
            high_price=quote_data["high"],
            low_price=quote_data["low"],
            close_price=quote_data["price"],
            volume=quote_data["volume"],
            data_source=quote_data["source"],
            is_real_time=True
        )

        db.add(price_record)
        db.commit()

        return stock
