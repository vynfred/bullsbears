"""
Stock Data Service - Primary: Alpha Vantage, Backup: Finnhub
Handles real-time quotes, historical data, and options chains with caching and rate limiting.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
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
    Stock data service with Alpha Vantage primary and Finnhub backup.
    Implements caching, rate limiting, and error handling.
    """

    def __init__(self):
        self.alpha_vantage_key = settings.alpha_vantage_api_key
        self.finnhub_key = settings.finnhub_api_key
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

        # Fallback to Finnhub
        try:
            quote_data = await self._fetch_finnhub_quote(symbol)
            if quote_data:
                # Cache for 30 seconds
                await redis_client.cache_with_ttl(cache_key, quote_data, settings.cache_api_responses)
                return quote_data
        except Exception as e:
            logger.error(f"Finnhub quote failed for {symbol}: {e}")

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

            if "Information" in data and "rate limit" in data["Information"].lower():
                raise Exception(f"API rate limit exceeded: {data['Information']}")

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
    
    async def _fetch_finnhub_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time quote from Finnhub."""
        if not self.finnhub_key:
            logger.warning("Finnhub key not configured")
            return None

        url = "https://finnhub.io/api/v1/quote"
        params = {
            "symbol": symbol,
            "token": self.finnhub_key
        }

        session = await self._get_session()
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Finnhub HTTP {response.status}")

            data = await response.json()

            if not data or data.get("c") is None:
                logger.warning(f"No quote data from Finnhub for {symbol}")
                return None

            current_price = float(data.get("c", 0))
            previous_close = float(data.get("pc", 0))
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close > 0 else 0

            return {
                "symbol": symbol,
                "price": current_price,
                "change": change,
                "change_percent": f"{change_percent:.2f}",
                "volume": 0,  # Finnhub doesn't provide volume in quote endpoint
                "open": float(data.get("o", 0)),
                "high": float(data.get("h", 0)),
                "low": float(data.get("l", 0)),
                "previous_close": previous_close,
                "timestamp": datetime.now(),
                "source": "finnhub"
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

        # Fallback to Finnhub
        try:
            historical_data = await self._fetch_finnhub_historical(symbol, period)
            if historical_data:
                await redis_client.cache_with_ttl(cache_key, historical_data, settings.cache_historical_data)
                return historical_data
        except Exception as e:
            logger.error(f"Finnhub historical failed for {symbol}: {e}")

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

            if "Information" in data and "rate limit" in data["Information"].lower():
                raise Exception(f"API rate limit exceeded: {data['Information']}")

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

    async def _fetch_finnhub_historical(self, symbol: str, period: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical data from Finnhub."""
        if not self.finnhub_key:
            logger.warning("Finnhub key not configured")
            return None

        # Map period to days
        period_days = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "10y": 3650,
            "ytd": 365,
            "max": 3650
        }

        days = period_days.get(period, 365)
        to_date = int(datetime.now().timestamp())
        from_date = int((datetime.now() - timedelta(days=days)).timestamp())

        url = "https://finnhub.io/api/v1/stock/candle"
        params = {
            "symbol": symbol,
            "resolution": "D",  # Daily resolution
            "from": from_date,
            "to": to_date,
            "token": self.finnhub_key
        }

        session = await self._get_session()
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Finnhub HTTP {response.status}")

            data = await response.json()

            if data.get("s") != "ok" or not data.get("c"):
                logger.warning(f"No historical data from Finnhub for {symbol}")
                return None

            historical_data = []
            timestamps = data.get("t", [])
            opens = data.get("o", [])
            highs = data.get("h", [])
            lows = data.get("l", [])
            closes = data.get("c", [])
            volumes = data.get("v", [])

            for i in range(len(timestamps)):
                date = datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
                historical_data.append({
                    "date": date,
                    "open": float(opens[i]),
                    "high": float(highs[i]),
                    "low": float(lows[i]),
                    "close": float(closes[i]),
                    "volume": int(volumes[i]) if i < len(volumes) else 0
                })

            # Sort by date (newest first)
            historical_data.sort(key=lambda x: x["date"], reverse=True)
            return historical_data

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_yf_historical)

    async def get_options_chain(self, symbol: str, expiration_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get options chain data with caching using Polygon.io.

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

        # Try Polygon.io for options data
        try:
            options_data = await self._fetch_polygon_options(symbol, expiration_date)
            if options_data:
                # Cache for 5 minutes
                await redis_client.cache_with_ttl(cache_key, options_data, 300)
                return options_data
        except Exception as e:
            logger.error(f"Polygon options failed for {symbol}: {e}")

        logger.error(f"Options data not available for {symbol}")
        return None

    async def _fetch_polygon_options(self, symbol: str, expiration_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch options chain from Polygon.io."""
        if not settings.polygon_api_key:
            logger.warning("Polygon API key not configured")
            return None

        session = await self._get_session()
        
        # Get available expiration dates first
        exp_url = f"https://api.polygon.io/v3/reference/options/contracts"
        exp_params = {
            "underlying_ticker": symbol,
            "contract_type": "option",
            "limit": 1000,
            "apikey": settings.polygon_api_key
        }

        try:
            async with session.get(exp_url, params=exp_params) as response:
                if response.status != 200:
                    raise Exception(f"Polygon HTTP {response.status}")

                data = await response.json()
                contracts = data.get("results", [])
                
                if not contracts:
                    logger.warning(f"No options contracts found for {symbol}")
                    return None

                # Extract unique expiration dates
                expirations = sorted(list(set(contract.get("expiration_date") for contract in contracts)))
                
                # Use first available expiration if none specified
                target_expiration = expiration_date or expirations[0] if expirations else None
                
                if not target_expiration:
                    return None

                # Filter contracts for target expiration
                target_contracts = [c for c in contracts if c.get("expiration_date") == target_expiration]
                
                # Get current quotes for these contracts
                calls = []
                puts = []
                
                for contract in target_contracts[:50]:  # Limit to prevent rate limiting
                    ticker = contract.get("ticker")
                    if not ticker:
                        continue
                        
                    # Get quote for this contract
                    quote_data = await self._fetch_polygon_option_quote(ticker)
                    
                    contract_data = {
                        "contract_symbol": ticker,
                        "strike": contract.get("strike_price"),
                        "expiration": contract.get("expiration_date"),
                        "last_price": quote_data.get("last_price", 0) if quote_data else 0,
                        "bid": quote_data.get("bid", 0) if quote_data else 0,
                        "ask": quote_data.get("ask", 0) if quote_data else 0,
                        "volume": quote_data.get("volume", 0) if quote_data else 0,
                        "open_interest": quote_data.get("open_interest", 0) if quote_data else 0,
                        "implied_volatility": quote_data.get("implied_volatility") if quote_data else None,
                        "delta": quote_data.get("delta") if quote_data else None,
                        "gamma": quote_data.get("gamma") if quote_data else None,
                        "theta": quote_data.get("theta") if quote_data else None,
                        "vega": quote_data.get("vega") if quote_data else None
                    }
                    
                    if contract.get("contract_type") == "call":
                        calls.append(contract_data)
                    else:
                        puts.append(contract_data)
                    
                    # Small delay to prevent rate limiting
                    await asyncio.sleep(0.1)

                return {
                    "symbol": symbol,
                    "expiration_date": target_expiration,
                    "available_expirations": expirations,
                    "calls": sorted(calls, key=lambda x: x["strike"]),
                    "puts": sorted(puts, key=lambda x: x["strike"]),
                    "source": "polygon"
                }

        except Exception as e:
            logger.error(f"Error fetching Polygon options for {symbol}: {e}")
            return None

    async def _fetch_polygon_option_quote(self, option_ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch individual option quote from Polygon."""
        if not settings.polygon_api_key:
            return None

        url = f"https://api.polygon.io/v2/last/trade/{option_ticker}"
        params = {"apikey": settings.polygon_api_key}

        session = await self._get_session()
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                result = data.get("results", {})
                
                return {
                    "last_price": result.get("p", 0),
                    "volume": result.get("s", 0),
                    "timestamp": result.get("t")
                }

        except Exception as e:
            logger.debug(f"Failed to get quote for {option_ticker}: {e}")
            return None

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
