"""
FRED Data Service - Federal Reserve Economic Data integration.

Integrates with FRED API to fetch:
- Federal funds rate
- Money supply (M1, M2)
- Economic indicators (GDP, unemployment, inflation)
- Treasury yields
- Consumer confidence

Follows precompute system patterns with daily batch processing and caching.
"""
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json

from ..core.config import settings
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


@dataclass
class EconomicIndicator:
    """Represents an economic indicator data point."""
    series_id: str
    series_name: str
    date: datetime
    value: float
    units: str
    frequency: str  # "Daily", "Weekly", "Monthly", "Quarterly", "Annual"


@dataclass
class FedRateData:
    """Represents Federal funds rate data."""
    date: datetime
    rate: float
    change_from_previous: Optional[float] = None
    trend: str = "Stable"  # "Rising", "Falling", "Stable"


class FREDDataService:
    """Service for fetching Federal Reserve Economic Data."""
    
    def __init__(self):
        self.api_key = settings.fred_api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting: 120 requests/minute per FRED API docs
        self.rate_limit_delay = 0.5  # 500ms between requests (conservative)
        self.last_request_time = 0.0
        
        # Cache TTLs (in seconds)
        self.daily_data_ttl = 86400  # 24 hours for daily data
        self.monthly_data_ttl = 86400 * 7  # 7 days for monthly data
        self.quarterly_data_ttl = 86400 * 30  # 30 days for quarterly data
        
        # Key economic series IDs
        self.series_ids = {
            "fed_funds_rate": "FEDFUNDS",
            "10_year_treasury": "GS10",
            "2_year_treasury": "GS2",
            "unemployment_rate": "UNRATE",
            "cpi_all_items": "CPIAUCSL",
            "gdp": "GDP",
            "money_supply_m1": "M1SL",
            "money_supply_m2": "M2SL",
            "consumer_confidence": "UMCSENT",
            "vix": "VIXCLS",
            "dollar_index": "DTWEXBGS"
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting (120 req/min = 2 req/sec)."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make rate-limited request to FRED API."""
        await self._rate_limit()
        
        params.update({
            "api_key": self.api_key,
            "file_type": "json"
        })
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limit hit, wait and retry
                    logger.warning(f"FRED API rate limit hit, waiting 60 seconds")
                    await asyncio.sleep(60)
                    return await self._make_request(endpoint, params)
                else:
                    logger.error(f"FRED API error {response.status}: {await response.text()}")
                    return {}
        except Exception as e:
            logger.error(f"FRED API request failed: {e}")
            return {}
    
    async def get_series_data(
        self, 
        series_id: str, 
        days_back: int = 365,
        use_cache: bool = True
    ) -> List[EconomicIndicator]:
        """
        Get time series data for a specific economic indicator.
        
        Args:
            series_id: FRED series ID (e.g., "FEDFUNDS")
            days_back: Number of days to look back
            use_cache: Whether to use cached data
            
        Returns:
            List of EconomicIndicator objects
        """
        cache_key = f"fred_series:{series_id}:{days_back}"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    indicators_data = json.loads(cached_data)
                    return [EconomicIndicator(**indicator) for indicator in indicators_data]
                except Exception as e:
                    logger.warning(f"Failed to parse cached FRED data: {e}")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get series info first
        series_info = await self._make_request("series", {"series_id": series_id})
        if not series_info or "seriess" not in series_info:
            logger.warning(f"No series info found for {series_id}")
            return []
        
        series_meta = series_info["seriess"][0]
        series_name = series_meta.get("title", series_id)
        units = series_meta.get("units", "")
        frequency = series_meta.get("frequency", "Unknown")
        
        # Get observations
        observations = await self._make_request("series/observations", {
            "series_id": series_id,
            "observation_start": start_date.strftime("%Y-%m-%d"),
            "observation_end": end_date.strftime("%Y-%m-%d"),
            "sort_order": "desc"
        })
        
        if not observations or "observations" not in observations:
            logger.warning(f"No observations found for {series_id}")
            return []
        
        indicators = []
        for obs in observations["observations"]:
            try:
                if obs["value"] != ".":  # FRED uses "." for missing values
                    indicator = EconomicIndicator(
                        series_id=series_id,
                        series_name=series_name,
                        date=datetime.strptime(obs["date"], "%Y-%m-%d"),
                        value=float(obs["value"]),
                        units=units,
                        frequency=frequency
                    )
                    indicators.append(indicator)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse observation: {e}")
                continue
        
        # Cache the results
        if use_cache and indicators:
            # Determine cache TTL based on frequency
            if frequency.lower() in ["daily", "weekly"]:
                cache_ttl = self.daily_data_ttl
            elif frequency.lower() == "monthly":
                cache_ttl = self.monthly_data_ttl
            else:
                cache_ttl = self.quarterly_data_ttl
            
            indicators_data = [indicator.__dict__ for indicator in indicators]
            # Convert datetime objects to ISO strings for JSON serialization
            for indicator_data in indicators_data:
                for key, value in indicator_data.items():
                    if isinstance(value, datetime):
                        indicator_data[key] = value.isoformat()
            
            await redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(indicators_data)
            )
        
        return indicators
    
    async def get_fed_funds_rate(self, use_cache: bool = True) -> Optional[FedRateData]:
        """
        Get current Federal funds rate with trend analysis.
        
        Args:
            use_cache: Whether to use cached data
            
        Returns:
            FedRateData object or None
        """
        indicators = await self.get_series_data("FEDFUNDS", days_back=90, use_cache=use_cache)
        
        if not indicators:
            return None
        
        # Sort by date (most recent first)
        indicators.sort(key=lambda x: x.date, reverse=True)
        
        current_rate = indicators[0].value
        current_date = indicators[0].date
        
        # Calculate trend
        if len(indicators) >= 2:
            previous_rate = indicators[1].value
            change = current_rate - previous_rate
            
            if change > 0.1:
                trend = "Rising"
            elif change < -0.1:
                trend = "Falling"
            else:
                trend = "Stable"
        else:
            change = None
            trend = "Stable"
        
        return FedRateData(
            date=current_date,
            rate=current_rate,
            change_from_previous=change,
            trend=trend
        )
    
    async def get_economic_snapshot(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get a comprehensive economic snapshot with key indicators.
        
        Args:
            use_cache: Whether to use cached data
            
        Returns:
            Dict with economic indicators and analysis
        """
        cache_key = "fred_economic_snapshot"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    return json.loads(cached_data)
                except Exception as e:
                    logger.warning(f"Failed to parse cached economic snapshot: {e}")
        
        # Fetch key indicators in parallel
        tasks = []
        key_series = ["FEDFUNDS", "GS10", "UNRATE", "CPIAUCSL", "UMCSENT"]
        
        for series_id in key_series:
            task = self.get_series_data(series_id, days_back=30, use_cache=use_cache)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "indicators": {},
            "market_sentiment": "Neutral",
            "economic_trend": "Stable"
        }
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {key_series[i]}: {result}")
                continue
            
            if result:
                series_id = key_series[i]
                latest = result[0]  # Most recent data point
                
                snapshot["indicators"][series_id] = {
                    "name": latest.series_name,
                    "value": latest.value,
                    "date": latest.date.isoformat(),
                    "units": latest.units
                }
        
        # Calculate market sentiment based on indicators
        sentiment_score = self._calculate_market_sentiment(snapshot["indicators"])
        
        if sentiment_score > 0.2:
            snapshot["market_sentiment"] = "Bullish"
        elif sentiment_score < -0.2:
            snapshot["market_sentiment"] = "Bearish"
        else:
            snapshot["market_sentiment"] = "Neutral"
        
        # Cache the snapshot
        if use_cache:
            await redis_client.setex(
                cache_key,
                3600,  # 1 hour cache
                json.dumps(snapshot)
            )
        
        return snapshot
    
    def _calculate_market_sentiment(self, indicators: Dict[str, Any]) -> float:
        """
        Calculate market sentiment score based on economic indicators.
        
        Returns:
            Float between -1.0 (very bearish) and 1.0 (very bullish)
        """
        sentiment_score = 0.0
        
        # Fed funds rate impact (lower rates = more bullish)
        if "FEDFUNDS" in indicators:
            fed_rate = indicators["FEDFUNDS"]["value"]
            if fed_rate < 2.0:
                sentiment_score += 0.3
            elif fed_rate > 5.0:
                sentiment_score -= 0.3
        
        # Unemployment rate impact (lower unemployment = more bullish)
        if "UNRATE" in indicators:
            unemployment = indicators["UNRATE"]["value"]
            if unemployment < 4.0:
                sentiment_score += 0.2
            elif unemployment > 6.0:
                sentiment_score -= 0.2
        
        # Consumer confidence impact
        if "UMCSENT" in indicators:
            confidence = indicators["UMCSENT"]["value"]
            if confidence > 90:
                sentiment_score += 0.2
            elif confidence < 70:
                sentiment_score -= 0.2
        
        return max(-1.0, min(1.0, sentiment_score))

    async def get_upcoming_economic_events(self, days_ahead: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get upcoming economic events for monitoring alerts.

        Args:
            days_ahead: Days to look ahead for events

        Returns:
            Dict with upcoming events or None
        """
        try:
            # In a real implementation, this would fetch from an economic calendar API
            # For now, we'll simulate upcoming events based on typical release schedules

            upcoming_events = []
            current_date = datetime.now()

            # Simulate typical economic events
            event_templates = [
                {
                    "name": "Federal Reserve Interest Rate Decision",
                    "frequency": 45,  # Every ~45 days
                    "market_impact_score": 0.8,
                    "description": "FOMC meeting and rate decision"
                },
                {
                    "name": "Consumer Price Index (CPI)",
                    "frequency": 30,  # Monthly
                    "market_impact_score": 0.6,
                    "description": "Monthly inflation data release"
                },
                {
                    "name": "Non-Farm Payrolls",
                    "frequency": 30,  # Monthly
                    "market_impact_score": 0.7,
                    "description": "Monthly employment report"
                },
                {
                    "name": "GDP Preliminary Report",
                    "frequency": 90,  # Quarterly
                    "market_impact_score": 0.5,
                    "description": "Quarterly economic growth data"
                }
            ]

            # Generate upcoming events within the specified window
            for template in event_templates:
                # Simulate next occurrence (simplified logic)
                import random
                random.seed(hash(template["name"]) % 1000)

                days_until = random.randint(1, days_ahead)
                event_date = current_date + timedelta(days=days_until)

                if days_until <= days_ahead:
                    upcoming_events.append({
                        "name": template["name"],
                        "date": event_date.isoformat(),
                        "market_impact_score": template["market_impact_score"],
                        "description": template["description"],
                        "days_until": days_until,
                        "source": "FRED_SIMULATED"
                    })

            return {
                "events": upcoming_events,
                "total_events": len(upcoming_events),
                "analysis_date": current_date.isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting upcoming economic events: {e}")
            return None
