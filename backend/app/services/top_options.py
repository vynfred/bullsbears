"""
Top Options Service - Manages the top 10 most traded options based on volume.

This service fetches the most active options from Finnhub API and falls back to
a curated static list of high-volume options when API limits are reached.

Volume context (as of 2024-2025):
- SPY: ~9M avg daily contracts (S&P 500 ETF)
- QQQ: ~4M avg daily contracts (NASDAQ 100 ETF)
- NVDA: ~2.9M avg daily contracts (AI/GPU leader)
- TSLA: ~2.5M avg daily contracts (EV leader)
- AAPL: ~2.2M avg daily contracts (Tech giant)
- AMZN: ~1.8M avg daily contracts (E-commerce/Cloud)
- META: ~1.5M avg daily contracts (Social media)
- MSFT: ~1.3M avg daily contracts (Cloud/Software)
- AMD: ~1.2M avg daily contracts (Semiconductor)
- PLTR: ~1.1M avg daily contracts (Data analytics)
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class TopOptionsService:
    """Service for managing top 10 most traded options."""
    
    def __init__(self):
        self.settings = get_settings()
        # Static fallback list based on 2024-2025 volume data
        self.static_top_10 = [
            "SPY",   # ~9M daily contracts - S&P 500 ETF
            "QQQ",   # ~4M daily contracts - NASDAQ 100 ETF  
            "NVDA",  # ~2.9M daily contracts - AI/GPU leader
            "TSLA",  # ~2.5M daily contracts - EV pioneer
            "AAPL",  # ~2.2M daily contracts - Tech giant
            "AMZN",  # ~1.8M daily contracts - E-commerce/Cloud
            "META",  # ~1.5M daily contracts - Social media
            "MSFT",  # ~1.3M daily contracts - Cloud/Software
            "AMD",   # ~1.2M daily contracts - Semiconductor
            "PLTR"   # ~1.1M daily contracts - Data analytics
        ]
        self.cache_duration = timedelta(minutes=15)
        self.last_fetch = None
        self.cached_symbols = None
    
    async def get_top_options_symbols(self) -> List[str]:
        """
        Get top 10 most traded options symbols.
        
        Returns:
            List of ticker symbols for the most active options
        """
        # Check if we have valid cached data
        if self._is_cache_valid():
            logger.info("Using cached top options symbols")
            return self.cached_symbols
        
        # Try to fetch from Finnhub API
        try:
            symbols = await self._fetch_from_finnhub()
            if symbols:
                self._update_cache(symbols)
                logger.info(f"Top 10 updated from Finnhub: {', '.join(symbols[:3])}... leads with sustained volume")
                return symbols
        except Exception as e:
            logger.warning(f"Failed to fetch from Finnhub: {e}")
        
        # Fallback to static list
        logger.info("Using static fallback list for top options")
        self._update_cache(self.static_top_10)
        return self.static_top_10
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self.cached_symbols or not self.last_fetch:
            return False
        return datetime.now() - self.last_fetch < self.cache_duration
    
    def _update_cache(self, symbols: List[str]):
        """Update the cache with new symbols."""
        self.cached_symbols = symbols
        self.last_fetch = datetime.now()
    
    async def _fetch_from_finnhub(self) -> Optional[List[str]]:
        """
        Fetch most active options from Finnhub API.
        
        Returns:
            List of ticker symbols or None if failed
        """
        if not self.settings.finnhub_api_key:
            logger.warning("Finnhub API key not configured")
            return None
        
        url = "https://finnhub.io/api/v1/scan/option-most-active"
        params = {
            "token": self.settings.finnhub_api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Extract symbols from Finnhub response
                        symbols = self._parse_finnhub_response(data)
                        return symbols[:10]  # Top 10 only
                    elif response.status == 429:
                        logger.warning("Finnhub rate limit reached")
                        return None
                    else:
                        logger.error(f"Finnhub API error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("Finnhub API timeout")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Finnhub: {e}")
            return None
    
    def _parse_finnhub_response(self, data: dict) -> List[str]:
        """
        Parse Finnhub API response to extract ticker symbols.
        
        Args:
            data: Raw response from Finnhub API
            
        Returns:
            List of ticker symbols
        """
        symbols = []
        try:
            # Finnhub returns different formats, handle common ones
            if isinstance(data, dict):
                if 'result' in data:
                    for item in data['result']:
                        if 'symbol' in item:
                            # Extract base symbol (remove option suffix)
                            symbol = item['symbol'].split('_')[0]
                            if symbol not in symbols and len(symbol) <= 5:
                                symbols.append(symbol)
                elif 'data' in data:
                    for item in data['data']:
                        if 'underlying' in item:
                            symbol = item['underlying']
                            if symbol not in symbols and len(symbol) <= 5:
                                symbols.append(symbol)
            
            # If parsing fails or returns empty, log and return empty
            if not symbols:
                logger.warning("Could not parse Finnhub response, no symbols found")
                
        except Exception as e:
            logger.error(f"Error parsing Finnhub response: {e}")
        
        return symbols
    
    async def get_options_info(self, symbol: str) -> dict:
        """
        Get additional options information for a symbol.
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Dictionary with options metadata
        """
        return {
            "symbol": symbol,
            "is_top_10": symbol in await self.get_top_options_symbols(),
            "estimated_daily_volume": self._get_estimated_volume(symbol),
            "liquidity_tier": self._get_liquidity_tier(symbol)
        }
    
    def _get_estimated_volume(self, symbol: str) -> str:
        """Get estimated daily volume for a symbol."""
        volume_map = {
            "SPY": "~9M contracts",
            "QQQ": "~4M contracts", 
            "NVDA": "~2.9M contracts",
            "TSLA": "~2.5M contracts",
            "AAPL": "~2.2M contracts",
            "AMZN": "~1.8M contracts",
            "META": "~1.5M contracts",
            "MSFT": "~1.3M contracts",
            "AMD": "~1.2M contracts",
            "PLTR": "~1.1M contracts"
        }
        return volume_map.get(symbol, "~500K+ contracts")
    
    def _get_liquidity_tier(self, symbol: str) -> str:
        """Get liquidity tier classification."""
        if symbol in ["SPY", "QQQ"]:
            return "ULTRA_HIGH"
        elif symbol in ["NVDA", "TSLA", "AAPL"]:
            return "VERY_HIGH"
        elif symbol in self.static_top_10:
            return "HIGH"
        else:
            return "MODERATE"

# Global instance
top_options_service = TopOptionsService()
