"""
FMP Options Service - Financial Modeling Prep API Integration
Handles options chains, expiration dates, and volume filtering for AI Options Review tool
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
from dataclasses import dataclass
import json

from ..core.config import settings
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class OptionContract:
    """Individual option contract data."""
    symbol: str
    contract_symbol: str
    option_type: str  # 'CALL' or 'PUT'
    strike: float
    expiration_date: str
    last_price: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    intrinsic_value: Optional[float] = None
    time_value: Optional[float] = None

@dataclass
class ExpirationInfo:
    """Expiration date information."""
    date: str  # YYYY-MM-DD
    display_date: str
    days_to_expiry: int
    is_weekly: bool
    is_monthly: bool
    is_quarterly: bool
    has_earnings: bool = False
    earnings_date: Optional[str] = None

@dataclass
class OptionsChainData:
    """Complete options chain data."""
    symbol: str
    current_price: float
    timestamp: str
    available_expirations: List[ExpirationInfo]
    calls: List[OptionContract]
    puts: List[OptionContract]
    iv_rank: Optional[float] = None
    earnings_date: Optional[str] = None

class FMPOptionsService:
    """Financial Modeling Prep API service for options data."""
    
    def __init__(self):
        self.api_key = settings.fmp_api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.session: Optional[aiohttp.ClientSession] = None
        self.redis_client = None
        
        # Volume thresholds for filtering
        self.low_volume_threshold = 200   # For low volume stocks
        self.high_volume_threshold = 1000 # For high volume stocks
        
        # Cache TTL settings
        self.expiration_cache_ttl = 3600  # 1 hour for expiration dates
        self.options_cache_ttl = 300      # 5 minutes for options data
        self.earnings_cache_ttl = 86400   # 24 hours for earnings data

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'BullsBears/2.1'}
        )
        self.redis_client = await get_redis_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_available_expirations(self, symbol: str) -> List[ExpirationInfo]:
        """
        Get available expiration dates for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of available expiration dates with metadata
        """
        cache_key = f"fmp:expirations:{symbol}"
        
        # Check cache first
        if self.redis_client:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for expirations {symbol}")
                return [ExpirationInfo(**exp) for exp in cached_data]

        try:
            # Get options chain to extract expiration dates
            url = f"{self.base_url}/options-chain/{symbol}"
            params = {"apikey": self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"FMP API error for {symbol}: {response.status}")
                    return []
                
                data = await response.json()
                
                if not data or not isinstance(data, list):
                    logger.warning(f"No options data available for {symbol}")
                    return []

                # Extract unique expiration dates
                expiration_dates = set()
                for option in data:
                    if 'expiration' in option:
                        expiration_dates.add(option['expiration'])

                # Convert to ExpirationInfo objects
                expirations = []
                today = datetime.now().date()
                
                # Get earnings data for this symbol
                earnings_date = await self._get_next_earnings_date(symbol)
                
                for exp_str in sorted(expiration_dates):
                    try:
                        exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                        days_to_expiry = (exp_date - today).days
                        
                        if days_to_expiry <= 0:
                            continue  # Skip expired options
                        
                        # Determine if it's weekly, monthly, or quarterly
                        is_monthly = exp_date.day >= 15 and exp_date.day <= 21 and exp_date.weekday() == 4  # Third Friday
                        is_weekly = exp_date.weekday() == 4 and not is_monthly  # Friday but not monthly
                        is_quarterly = is_monthly and exp_date.month in [3, 6, 9, 12]
                        
                        # Check if earnings is near this expiration
                        has_earnings = False
                        if earnings_date:
                            earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                            days_to_earnings = abs((exp_date - earnings_dt).days)
                            has_earnings = days_to_earnings <= 7  # Within a week
                        
                        expirations.append(ExpirationInfo(
                            date=exp_str,
                            display_date=exp_date.strftime('%b %d' + (', %Y' if exp_date.year != today.year else '')),
                            days_to_expiry=days_to_expiry,
                            is_weekly=is_weekly,
                            is_monthly=is_monthly,
                            is_quarterly=is_quarterly,
                            has_earnings=has_earnings,
                            earnings_date=earnings_date if has_earnings else None
                        ))
                        
                    except ValueError as e:
                        logger.warning(f"Invalid expiration date format {exp_str}: {e}")
                        continue

                # Cache the results
                if self.redis_client and expirations:
                    cache_data = [exp.__dict__ for exp in expirations]
                    await self.redis_client.setex(cache_key, self.expiration_cache_ttl, json.dumps(cache_data))

                return expirations

        except Exception as e:
            logger.error(f"Error fetching expirations for {symbol}: {e}")
            return []

    async def get_options_chain(self, symbol: str, expiration_date: Optional[str] = None) -> Optional[OptionsChainData]:
        """
        Get options chain data with volume filtering.
        
        Args:
            symbol: Stock symbol
            expiration_date: Specific expiration date (YYYY-MM-DD) or None for all
            
        Returns:
            Complete options chain data with volume filtering applied
        """
        cache_key = f"fmp:options:{symbol}:{expiration_date or 'all'}"
        
        # Check cache first
        if self.redis_client:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for options chain {symbol}")
                return OptionsChainData(**cached_data)

        try:
            # Get current stock price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return None

            # Get options chain
            url = f"{self.base_url}/options-chain/{symbol}"
            params = {"apikey": self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"FMP API error for {symbol}: {response.status}")
                    return None
                
                data = await response.json()
                
                if not data or not isinstance(data, list):
                    logger.warning(f"No options data available for {symbol}")
                    return None

                # Determine volume threshold based on stock characteristics
                volume_threshold = await self._determine_volume_threshold(symbol, current_price)
                
                # Process options data
                calls = []
                puts = []
                available_expirations = set()
                
                for option in data:
                    try:
                        # Skip if specific expiration requested and doesn't match
                        if expiration_date and option.get('expiration') != expiration_date:
                            continue
                        
                        # Apply volume filtering
                        volume = option.get('volume', 0)
                        if volume < volume_threshold:
                            continue
                        
                        # Create option contract
                        contract = OptionContract(
                            symbol=symbol,
                            contract_symbol=option.get('contractSymbol', ''),
                            option_type=option.get('type', '').upper(),
                            strike=float(option.get('strike', 0)),
                            expiration_date=option.get('expiration', ''),
                            last_price=float(option.get('lastPrice', 0)),
                            bid=float(option.get('bid', 0)),
                            ask=float(option.get('ask', 0)),
                            volume=volume,
                            open_interest=option.get('openInterest', 0),
                            implied_volatility=float(option.get('impliedVolatility', 0)),
                            delta=option.get('delta'),
                            gamma=option.get('gamma'),
                            theta=option.get('theta'),
                            vega=option.get('vega'),
                            rho=option.get('rho')
                        )
                        
                        # Calculate intrinsic and time value
                        if contract.option_type == 'CALL':
                            contract.intrinsic_value = max(0, current_price - contract.strike)
                        else:
                            contract.intrinsic_value = max(0, contract.strike - current_price)
                        
                        contract.time_value = contract.last_price - contract.intrinsic_value
                        
                        # Add to appropriate list
                        if contract.option_type == 'CALL':
                            calls.append(contract)
                        else:
                            puts.append(contract)
                        
                        available_expirations.add(contract.expiration_date)
                        
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Error processing option data: {e}")
                        continue

                # Get expiration info for available dates
                expiration_infos = []
                if available_expirations:
                    all_expirations = await self.get_available_expirations(symbol)
                    expiration_infos = [exp for exp in all_expirations if exp.date in available_expirations]

                # Calculate IV rank (simplified)
                iv_rank = await self._calculate_iv_rank(symbol, calls + puts)
                
                # Get earnings date
                earnings_date = await self._get_next_earnings_date(symbol)

                # Create options chain data
                options_chain = OptionsChainData(
                    symbol=symbol,
                    current_price=current_price,
                    timestamp=datetime.now().isoformat(),
                    available_expirations=expiration_infos,
                    calls=sorted(calls, key=lambda x: x.strike),
                    puts=sorted(puts, key=lambda x: x.strike),
                    iv_rank=iv_rank,
                    earnings_date=earnings_date
                )

                # Cache the results
                if self.redis_client:
                    cache_data = {
                        'symbol': options_chain.symbol,
                        'current_price': options_chain.current_price,
                        'timestamp': options_chain.timestamp,
                        'available_expirations': [exp.__dict__ for exp in options_chain.available_expirations],
                        'calls': [call.__dict__ for call in options_chain.calls],
                        'puts': [put.__dict__ for put in options_chain.puts],
                        'iv_rank': options_chain.iv_rank,
                        'earnings_date': options_chain.earnings_date
                    }
                    await self.redis_client.setex(cache_key, self.options_cache_ttl, json.dumps(cache_data))

                return options_chain

        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return None

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price from FMP API."""
        try:
            url = f"{self.base_url}/quote-short/{symbol}"
            params = {"apikey": self.api_key}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return float(data[0].get('price', 0))

        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")

        return None

    async def _determine_volume_threshold(self, symbol: str, current_price: float) -> int:
        """
        Determine volume threshold based on stock characteristics.

        Args:
            symbol: Stock symbol
            current_price: Current stock price

        Returns:
            Volume threshold for filtering options
        """
        try:
            # Get average volume to determine if it's a high or low volume stock
            url = f"{self.base_url}/profile/{symbol}"
            params = {"apikey": self.api_key}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        avg_volume = data[0].get('volAvg', 0)
                        market_cap = data[0].get('mktCap', 0)

                        # High volume stocks (>10M avg volume or >50B market cap)
                        if avg_volume > 10_000_000 or market_cap > 50_000_000_000:
                            return self.high_volume_threshold

        except Exception as e:
            logger.warning(f"Could not determine volume characteristics for {symbol}: {e}")

        # Default to low volume threshold
        return self.low_volume_threshold

    async def _get_next_earnings_date(self, symbol: str) -> Optional[str]:
        """Get next earnings date for the symbol."""
        cache_key = f"fmp:earnings:{symbol}"

        # Check cache first
        if self.redis_client:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return cached_data

        try:
            # Get earnings calendar
            today = datetime.now().strftime('%Y-%m-%d')
            future_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

            url = f"{self.base_url}/earning_calendar"
            params = {
                "apikey": self.api_key,
                "from": today,
                "to": future_date
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if not data or not isinstance(data, list):
                    return None

                # Find earnings for this symbol
                for earnings in data:
                    if earnings.get('symbol') == symbol:
                        earnings_date = earnings.get('date')
                        if earnings_date:
                            # Cache the result
                            if self.redis_client:
                                await self.redis_client.setex(cache_key, self.earnings_cache_ttl, earnings_date)
                            return earnings_date

        except Exception as e:
            logger.error(f"Error fetching earnings date for {symbol}: {e}")

        return None

    async def _calculate_iv_rank(self, symbol: str, options: List[OptionContract]) -> Optional[float]:
        """
        Calculate IV rank (simplified version).

        Args:
            symbol: Stock symbol
            options: List of option contracts

        Returns:
            IV rank as percentage (0-100)
        """
        if not options:
            return None

        try:
            # Get current average IV
            ivs = [opt.implied_volatility for opt in options if opt.implied_volatility > 0]
            if not ivs:
                return None

            current_iv = sum(ivs) / len(ivs)

            # For a proper IV rank, we'd need historical IV data
            # For now, return a simplified calculation based on current IV levels
            # This is a placeholder - in production, you'd want historical IV data

            if current_iv < 0.2:  # Low IV
                return 25.0
            elif current_iv < 0.4:  # Medium IV
                return 50.0
            elif current_iv < 0.6:  # High IV
                return 75.0
            else:  # Very high IV
                return 90.0

        except Exception as e:
            logger.error(f"Error calculating IV rank for {symbol}: {e}")
            return None

    async def validate_symbol(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a symbol exists and get company name.

        Args:
            symbol: Stock symbol to validate

        Returns:
            Tuple of (is_valid, company_name)
        """
        try:
            url = f"{self.base_url}/profile/{symbol}"
            params = {"apikey": self.api_key}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return False, None

                data = await response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    company_name = data[0].get('companyName', symbol)
                    return True, company_name

        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")

        return False, None
