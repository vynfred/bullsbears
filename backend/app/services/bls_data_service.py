"""
BLS Data Service - Bureau of Labor Statistics data integration.

Integrates with BLS API to fetch:
- Consumer Price Index (CPI) data
- Employment statistics
- Inflation data
- Producer Price Index (PPI)
- Labor force statistics

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
class BLSDataPoint:
    """Represents a BLS data point."""
    series_id: str
    series_name: str
    year: int
    period: str  # "M01", "M02", etc. for monthly data
    period_name: str  # "January", "February", etc.
    value: float
    date: datetime
    footnotes: Optional[List[str]] = None


@dataclass
class CPIData:
    """Represents Consumer Price Index data."""
    date: datetime
    cpi_value: float
    monthly_change: Optional[float] = None
    annual_change: Optional[float] = None
    trend: str = "Stable"  # "Rising", "Falling", "Stable"


@dataclass
class EmploymentData:
    """Represents employment statistics."""
    date: datetime
    unemployment_rate: float
    labor_force_participation: Optional[float] = None
    nonfarm_payrolls: Optional[int] = None
    trend: str = "Stable"


class BLSDataService:
    """Service for fetching Bureau of Labor Statistics data."""
    
    def __init__(self):
        self.api_key = settings.bls_api_key
        self.base_url = "https://api.bls.gov/publicAPI/v2/timeseries/data"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting: 500 queries/day, 50 series/query for registered users
        self.rate_limit_delay = 0.2  # 200ms between requests (conservative)
        self.last_request_time = 0.0
        self.daily_request_count = 0
        self.max_daily_requests = 450  # Leave buffer
        
        # Cache TTLs (in seconds)
        self.monthly_data_ttl = 86400 * 7  # 7 days for monthly data
        self.daily_data_ttl = 86400  # 24 hours for daily data
        
        # Key BLS series IDs
        self.series_ids = {
            # Consumer Price Index
            "cpi_all_items": "CUUR0000SA0",  # CPI-U All Items
            "cpi_core": "CUUR0000SA0L1E",   # CPI-U Core (less food & energy)
            "cpi_food": "CUUR0000SAF1",     # CPI-U Food
            "cpi_energy": "CUUR0000SAE",    # CPI-U Energy
            "cpi_housing": "CUUR0000SAH1",  # CPI-U Housing
            
            # Producer Price Index
            "ppi_final_demand": "WPUFD49207",  # PPI Final Demand
            "ppi_commodities": "WPUSOP3000",   # PPI Commodities
            
            # Employment
            "unemployment_rate": "LNS14000000",      # Unemployment Rate
            "labor_force_participation": "LNS11300000",  # Labor Force Participation Rate
            "nonfarm_payrolls": "CES0000000001",     # Total Nonfarm Payrolls
            "average_hourly_earnings": "CES0500000003",  # Average Hourly Earnings
            
            # Industry-specific employment
            "manufacturing_employment": "CES3000000001",  # Manufacturing Employment
            "retail_employment": "CES4200000001",         # Retail Trade Employment
            "tech_employment": "CES5415000001"            # Computer Systems Design Employment
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
        """Enforce rate limiting and daily quota."""
        if self.daily_request_count >= self.max_daily_requests:
            logger.warning("BLS API daily quota reached")
            raise Exception("BLS API daily quota exceeded")
        
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
        self.daily_request_count += 1
    
    async def _make_request(self, series_ids: List[str], start_year: int, end_year: int) -> Dict[str, Any]:
        """Make rate-limited request to BLS API."""
        await self._rate_limit()
        
        payload = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
            "registrationkey": self.api_key
        }
        
        try:
            async with self.session.post(
                self.base_url, 
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limit hit, wait and retry
                    logger.warning(f"BLS API rate limit hit, waiting 60 seconds")
                    await asyncio.sleep(60)
                    return await self._make_request(series_ids, start_year, end_year)
                else:
                    logger.error(f"BLS API error {response.status}: {await response.text()}")
                    return {}
        except Exception as e:
            logger.error(f"BLS API request failed: {e}")
            return {}
    
    async def get_cpi_data(
        self, 
        months_back: int = 12,
        use_cache: bool = True
    ) -> List[CPIData]:
        """
        Get Consumer Price Index data.
        
        Args:
            months_back: Number of months to look back
            use_cache: Whether to use cached data
            
        Returns:
            List of CPIData objects
        """
        cache_key = f"bls_cpi:{months_back}"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    cpi_data = json.loads(cached_data)
                    return [CPIData(**data) for data in cpi_data]
                except Exception as e:
                    logger.warning(f"Failed to parse cached CPI data: {e}")
        
        # Calculate year range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        start_year = start_date.year
        end_year = end_date.year
        
        # Fetch CPI data
        response = await self._make_request(
            [self.series_ids["cpi_all_items"], self.series_ids["cpi_core"]], 
            start_year, 
            end_year
        )
        
        if not response or "Results" not in response:
            logger.warning("No CPI data found")
            return []
        
        cpi_data = []
        for series in response["Results"]["series"]:
            series_id = series["seriesID"]
            
            for data_point in series["data"]:
                try:
                    # Parse period (M01, M02, etc.)
                    period = data_point["period"]
                    if not period.startswith("M"):
                        continue  # Skip non-monthly data
                    
                    month = int(period[1:])
                    year = int(data_point["year"])
                    
                    # Create date
                    date = datetime(year, month, 1)
                    
                    # Skip if outside our date range
                    if date < start_date:
                        continue
                    
                    cpi_value = float(data_point["value"])
                    
                    cpi_data.append(CPIData(
                        date=date,
                        cpi_value=cpi_value,
                        monthly_change=None,  # Will calculate below
                        annual_change=None,   # Will calculate below
                        trend="Stable"
                    ))
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse CPI data point: {e}")
                    continue
        
        # Sort by date and calculate changes
        cpi_data.sort(key=lambda x: x.date)
        
        for i, data in enumerate(cpi_data):
            # Calculate monthly change
            if i > 0:
                prev_value = cpi_data[i-1].cpi_value
                data.monthly_change = ((data.cpi_value - prev_value) / prev_value) * 100
            
            # Calculate annual change
            if i >= 12:
                year_ago_value = cpi_data[i-12].cpi_value
                data.annual_change = ((data.cpi_value - year_ago_value) / year_ago_value) * 100
            
            # Determine trend
            if data.monthly_change:
                if data.monthly_change > 0.2:
                    data.trend = "Rising"
                elif data.monthly_change < -0.2:
                    data.trend = "Falling"
                else:
                    data.trend = "Stable"
        
        # Cache the results
        if use_cache and cpi_data:
            cpi_data_dict = []
            for data in cpi_data:
                data_dict = data.__dict__.copy()
                data_dict["date"] = data.date.isoformat()
                cpi_data_dict.append(data_dict)
            
            await redis_client.setex(
                cache_key,
                self.monthly_data_ttl,
                json.dumps(cpi_data_dict)
            )
        
        return cpi_data
    
    async def get_employment_data(
        self, 
        months_back: int = 12,
        use_cache: bool = True
    ) -> List[EmploymentData]:
        """
        Get employment statistics.
        
        Args:
            months_back: Number of months to look back
            use_cache: Whether to use cached data
            
        Returns:
            List of EmploymentData objects
        """
        cache_key = f"bls_employment:{months_back}"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    employment_data = json.loads(cached_data)
                    return [EmploymentData(**data) for data in employment_data]
                except Exception as e:
                    logger.warning(f"Failed to parse cached employment data: {e}")
        
        # Calculate year range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        start_year = start_date.year
        end_year = end_date.year
        
        # Fetch employment data
        employment_series = [
            self.series_ids["unemployment_rate"],
            self.series_ids["labor_force_participation"],
            self.series_ids["nonfarm_payrolls"]
        ]
        
        response = await self._make_request(employment_series, start_year, end_year)
        
        if not response or "Results" not in response:
            logger.warning("No employment data found")
            return []
        
        # Process employment data
        employment_by_date = {}
        
        for series in response["Results"]["series"]:
            series_id = series["seriesID"]
            
            for data_point in series["data"]:
                try:
                    period = data_point["period"]
                    if not period.startswith("M"):
                        continue
                    
                    month = int(period[1:])
                    year = int(data_point["year"])
                    date = datetime(year, month, 1)
                    
                    if date < start_date:
                        continue
                    
                    value = float(data_point["value"])
                    
                    if date not in employment_by_date:
                        employment_by_date[date] = {}
                    
                    employment_by_date[date][series_id] = value
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse employment data point: {e}")
                    continue
        
        # Create EmploymentData objects
        employment_data = []
        for date, data in employment_by_date.items():
            unemployment_rate = data.get(self.series_ids["unemployment_rate"])
            labor_force_participation = data.get(self.series_ids["labor_force_participation"])
            nonfarm_payrolls = data.get(self.series_ids["nonfarm_payrolls"])
            
            if unemployment_rate is not None:
                employment_data.append(EmploymentData(
                    date=date,
                    unemployment_rate=unemployment_rate,
                    labor_force_participation=labor_force_participation,
                    nonfarm_payrolls=int(nonfarm_payrolls * 1000) if nonfarm_payrolls else None,  # Convert to actual number
                    trend="Stable"
                ))
        
        # Sort by date and calculate trends
        employment_data.sort(key=lambda x: x.date)
        
        for i, data in enumerate(employment_data):
            if i > 0:
                prev_unemployment = employment_data[i-1].unemployment_rate
                change = data.unemployment_rate - prev_unemployment
                
                if change > 0.2:
                    data.trend = "Rising"  # Rising unemployment = bearish
                elif change < -0.2:
                    data.trend = "Falling"  # Falling unemployment = bullish
                else:
                    data.trend = "Stable"
        
        # Cache the results
        if use_cache and employment_data:
            employment_data_dict = []
            for data in employment_data:
                data_dict = data.__dict__.copy()
                data_dict["date"] = data.date.isoformat()
                employment_data_dict.append(data_dict)
            
            await redis_client.setex(
                cache_key,
                self.monthly_data_ttl,
                json.dumps(employment_data_dict)
            )
        
        return employment_data
    
    async def get_inflation_impact_score(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Calculate inflation impact score for market analysis.
        
        Args:
            use_cache: Whether to use cached data
            
        Returns:
            Dict with inflation analysis and impact score
        """
        cpi_data = await self.get_cpi_data(months_back=6, use_cache=use_cache)
        
        if not cpi_data:
            return {
                "impact_score": 0.0,
                "confidence": 0.0,
                "current_inflation": 0.0,
                "trend": "Unknown",
                "market_impact": "Neutral"
            }
        
        # Get latest CPI data
        latest_cpi = cpi_data[-1]
        current_inflation = latest_cpi.annual_change or 0.0
        
        # Calculate impact score based on inflation level and trend
        impact_score = 0.0
        
        # High inflation is generally bearish for stocks
        if current_inflation > 4.0:
            impact_score -= 0.3
        elif current_inflation > 2.5:
            impact_score -= 0.1
        elif current_inflation < 1.0:
            impact_score += 0.1  # Very low inflation can be bullish
        
        # Factor in trend
        if latest_cpi.trend == "Rising" and current_inflation > 2.0:
            impact_score -= 0.2  # Rising inflation is bearish
        elif latest_cpi.trend == "Falling" and current_inflation > 3.0:
            impact_score += 0.1  # Falling inflation from high levels is bullish
        
        # Determine market impact
        if impact_score < -0.2:
            market_impact = "Bearish"
        elif impact_score > 0.1:
            market_impact = "Bullish"
        else:
            market_impact = "Neutral"
        
        return {
            "impact_score": round(impact_score, 3),
            "confidence": 0.8,  # High confidence in CPI data
            "current_inflation": round(current_inflation, 2),
            "trend": latest_cpi.trend,
            "market_impact": market_impact,
            "last_updated": latest_cpi.date.isoformat()
        }

    async def get_upcoming_releases(self, days_ahead: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get upcoming BLS data releases for monitoring alerts.

        Args:
            days_ahead: Days to look ahead for releases

        Returns:
            Dict with upcoming releases or None
        """
        try:
            # In a real implementation, this would fetch from BLS release calendar
            # For now, we'll simulate upcoming releases based on typical schedules

            upcoming_releases = []
            current_date = datetime.now()

            # Simulate typical BLS releases
            release_templates = [
                {
                    "name": "Consumer Price Index (CPI)",
                    "frequency": 30,  # Monthly
                    "market_impact_score": 0.7,
                    "description": "Monthly inflation data from Bureau of Labor Statistics"
                },
                {
                    "name": "Producer Price Index (PPI)",
                    "frequency": 30,  # Monthly
                    "market_impact_score": 0.5,
                    "description": "Wholesale price inflation data"
                },
                {
                    "name": "Employment Situation Report",
                    "frequency": 30,  # Monthly
                    "market_impact_score": 0.8,
                    "description": "Monthly employment and unemployment data"
                },
                {
                    "name": "Consumer Expenditure Survey",
                    "frequency": 90,  # Quarterly
                    "market_impact_score": 0.4,
                    "description": "Quarterly consumer spending patterns"
                }
            ]

            # Generate upcoming releases within the specified window
            for template in release_templates:
                # Simulate next occurrence (simplified logic)
                import random
                random.seed(hash(template["name"]) % 1000)

                days_until = random.randint(1, days_ahead)
                release_date = current_date + timedelta(days=days_until)

                if days_until <= days_ahead:
                    upcoming_releases.append({
                        "name": template["name"],
                        "date": release_date.isoformat(),
                        "market_impact_score": template["market_impact_score"],
                        "description": template["description"],
                        "days_until": days_until,
                        "source": "BLS_SIMULATED"
                    })

            return {
                "releases": upcoming_releases,
                "total_releases": len(upcoming_releases),
                "analysis_date": current_date.isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting upcoming BLS releases: {e}")
            return None
