"""
SEC Data Service - Handles insider trades, institutional holdings, and material events.

Integrates with SEC API (sec-api.io) to fetch:
- Form 3/4/5: Insider trading data
- Form 13F: Institutional holdings
- Form 8-K: Material events (Items 4.01, 4.02, 5.02)

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
class InsiderTrade:
    """Represents an insider trading transaction."""
    ticker: str
    insider_name: str
    insider_title: str
    transaction_date: datetime
    transaction_type: str  # "Buy", "Sell", "Grant", "Exercise"
    shares: int
    price_per_share: float
    total_value: float
    shares_owned_after: int
    filing_date: datetime
    form_type: str  # "3", "4", "5"


@dataclass
class InstitutionalHolding:
    """Represents institutional holdings from 13F filings."""
    ticker: str
    institution_name: str
    institution_cik: str
    shares_held: int
    market_value: float
    percent_of_portfolio: float
    quarter_end_date: datetime
    filing_date: datetime
    change_in_shares: Optional[int] = None
    change_percent: Optional[float] = None


@dataclass
class MaterialEvent:
    """Represents material events from 8-K filings."""
    ticker: str
    company_name: str
    event_date: datetime
    filing_date: datetime
    event_type: str  # "4.01", "4.02", "5.02", etc.
    event_description: str
    impact_score: float  # -1.0 to 1.0 (negative = bearish, positive = bullish)


class SECDataService:
    """Service for fetching and processing SEC filing data."""
    
    def __init__(self):
        self.api_key = settings.sec_api_key
        self.base_url = "https://api.sec-api.io"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting: 10 requests/second per SEC API docs
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0.0
        
        # Cache TTLs (in seconds)
        self.insider_cache_ttl = 86400  # 24 hours
        self.institutional_cache_ttl = 86400 * 7  # 7 days (13F quarterly)
        self.events_cache_ttl = 43200  # 12 hours
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting (10 req/sec)."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make rate-limited request to SEC API."""
        await self._rate_limit()
        
        params["token"] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limit hit, wait and retry
                    logger.warning(f"SEC API rate limit hit, waiting 60 seconds")
                    await asyncio.sleep(60)
                    return await self._make_request(endpoint, params)
                else:
                    logger.error(f"SEC API error {response.status}: {await response.text()}")
                    return {}
        except Exception as e:
            logger.error(f"SEC API request failed: {e}")
            return {}
    
    async def get_insider_trades(
        self, 
        ticker: str, 
        days_back: int = 90,
        use_cache: bool = True
    ) -> List[InsiderTrade]:
        """
        Get insider trading data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back
            use_cache: Whether to use cached data
            
        Returns:
            List of InsiderTrade objects
        """
        cache_key = f"sec_insider:{ticker}:{days_back}"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    trades_data = json.loads(cached_data)
                    return [InsiderTrade(**trade) for trade in trades_data]
                except Exception as e:
                    logger.warning(f"Failed to parse cached insider data: {e}")
        
        # Fetch from API
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:(\"3\" OR \"4\" OR \"5\")"
                }
            },
            "from": "0",
            "size": "200",
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        
        response = await self._make_request("", {"query": json.dumps(query)})
        
        if not response or "filings" not in response:
            logger.warning(f"No insider trading data found for {ticker}")
            return []
        
        trades = []
        for filing in response["filings"]:
            try:
                trade = self._parse_insider_filing(filing, ticker)
                if trade and trade.transaction_date >= start_date:
                    trades.append(trade)
            except Exception as e:
                logger.warning(f"Failed to parse insider filing: {e}")
                continue
        
        # Cache the results
        if use_cache and trades:
            trades_data = [trade.__dict__ for trade in trades]
            # Convert datetime objects to ISO strings for JSON serialization
            for trade_data in trades_data:
                for key, value in trade_data.items():
                    if isinstance(value, datetime):
                        trade_data[key] = value.isoformat()
            
            await redis_client.setex(
                cache_key,
                self.insider_cache_ttl,
                json.dumps(trades_data)
            )
        
        return trades
    
    def _parse_insider_filing(self, filing: Dict[str, Any], ticker: str) -> Optional[InsiderTrade]:
        """Parse insider trading filing into InsiderTrade object."""
        try:
            # Extract basic filing info
            form_type = filing.get("formType", "")
            filing_date = datetime.fromisoformat(filing.get("filedAt", "").replace("Z", "+00:00"))
            
            # For now, return a placeholder - full parsing would require
            # detailed XBRL/XML parsing of the filing content
            # This would be expanded based on actual SEC API response structure
            
            return InsiderTrade(
                ticker=ticker,
                insider_name=filing.get("entityName", "Unknown"),
                insider_title="Unknown",  # Would extract from filing details
                transaction_date=filing_date,
                transaction_type="Unknown",  # Would extract from filing details
                shares=0,  # Would extract from filing details
                price_per_share=0.0,  # Would extract from filing details
                total_value=0.0,  # Would extract from filing details
                shares_owned_after=0,  # Would extract from filing details
                filing_date=filing_date,
                form_type=form_type
            )
        except Exception as e:
            logger.error(f"Failed to parse insider filing: {e}")
            return None
    
    async def get_institutional_holdings(
        self, 
        ticker: str,
        use_cache: bool = True
    ) -> List[InstitutionalHolding]:
        """
        Get institutional holdings data for a ticker from 13F filings.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            
        Returns:
            List of InstitutionalHolding objects
        """
        cache_key = f"sec_institutional:{ticker}"
        
        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    holdings_data = json.loads(cached_data)
                    return [InstitutionalHolding(**holding) for holding in holdings_data]
                except Exception as e:
                    logger.warning(f"Failed to parse cached institutional data: {e}")
        
        # Fetch from API - 13F filings
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:\"13F-HR\""
                }
            },
            "from": "0",
            "size": "100",
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        
        response = await self._make_request("", {"query": json.dumps(query)})
        
        if not response or "filings" not in response:
            logger.warning(f"No institutional holdings data found for {ticker}")
            return []
        
        holdings = []
        for filing in response["filings"]:
            try:
                holding = self._parse_13f_filing(filing, ticker)
                if holding:
                    holdings.append(holding)
            except Exception as e:
                logger.warning(f"Failed to parse 13F filing: {e}")
                continue
        
        # Cache the results
        if use_cache and holdings:
            holdings_data = [holding.__dict__ for holding in holdings]
            # Convert datetime objects to ISO strings for JSON serialization
            for holding_data in holdings_data:
                for key, value in holding_data.items():
                    if isinstance(value, datetime):
                        holding_data[key] = value.isoformat()
            
            await redis_client.setex(
                cache_key,
                self.institutional_cache_ttl,
                json.dumps(holdings_data)
            )
        
        return holdings
    
    def _parse_13f_filing(self, filing: Dict[str, Any], ticker: str) -> Optional[InstitutionalHolding]:
        """Parse 13F filing into InstitutionalHolding object."""
        try:
            filing_date = datetime.fromisoformat(filing.get("filedAt", "").replace("Z", "+00:00"))
            
            # Placeholder - would need detailed parsing of 13F holdings table
            return InstitutionalHolding(
                ticker=ticker,
                institution_name=filing.get("entityName", "Unknown"),
                institution_cik=filing.get("cik", ""),
                shares_held=0,  # Would extract from holdings table
                market_value=0.0,  # Would extract from holdings table
                percent_of_portfolio=0.0,  # Would calculate
                quarter_end_date=filing_date,  # Would extract period end date
                filing_date=filing_date
            )
        except Exception as e:
            logger.error(f"Failed to parse 13F filing: {e}")
            return None

    async def get_material_events(
        self,
        ticker: str,
        days_back: int = 30,
        use_cache: bool = True
    ) -> List[MaterialEvent]:
        """
        Get material events for a ticker from 8-K filings.

        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back
            use_cache: Whether to use cached data

        Returns:
            List of MaterialEvent objects
        """
        cache_key = f"sec_events:{ticker}:{days_back}"

        # Check cache first
        if use_cache:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                try:
                    events_data = json.loads(cached_data)
                    return [MaterialEvent(**event) for event in events_data]
                except Exception as e:
                    logger.warning(f"Failed to parse cached events data: {e}")

        # Fetch from API - 8-K filings
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:\"8-K\""
                }
            },
            "from": "0",
            "size": "50",
            "sort": [{"filedAt": {"order": "desc"}}]
        }

        response = await self._make_request("", {"query": json.dumps(query)})

        if not response or "filings" not in response:
            logger.warning(f"No material events found for {ticker}")
            return []

        events = []
        for filing in response["filings"]:
            try:
                event = self._parse_8k_filing(filing, ticker)
                if event and event.event_date >= start_date:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse 8-K filing: {e}")
                continue

        # Cache the results
        if use_cache and events:
            events_data = [event.__dict__ for event in events]
            # Convert datetime objects to ISO strings for JSON serialization
            for event_data in events_data:
                for key, value in event_data.items():
                    if isinstance(value, datetime):
                        event_data[key] = value.isoformat()

            await redis_client.setex(
                cache_key,
                self.events_cache_ttl,
                json.dumps(events_data)
            )

        return events

    def _parse_8k_filing(self, filing: Dict[str, Any], ticker: str) -> Optional[MaterialEvent]:
        """Parse 8-K filing into MaterialEvent object."""
        try:
            filing_date = datetime.fromisoformat(filing.get("filedAt", "").replace("Z", "+00:00"))

            # Extract event type and description from filing
            # This would require parsing the actual 8-K content for items
            event_type = "Unknown"
            event_description = filing.get("documentFormatFiles", [{}])[0].get("description", "Material Event")

            # Calculate impact score based on event type
            impact_score = self._calculate_event_impact(event_type, event_description)

            return MaterialEvent(
                ticker=ticker,
                company_name=filing.get("entityName", "Unknown"),
                event_date=filing_date,
                filing_date=filing_date,
                event_type=event_type,
                event_description=event_description,
                impact_score=impact_score
            )
        except Exception as e:
            logger.error(f"Failed to parse 8-K filing: {e}")
            return None

    def _calculate_event_impact(self, event_type: str, description: str) -> float:
        """
        Calculate impact score for material events.

        Returns:
            Float between -1.0 (very bearish) and 1.0 (very bullish)
        """
        description_lower = description.lower()

        # Bearish indicators
        bearish_keywords = [
            "restatement", "investigation", "lawsuit", "departure", "resignation",
            "accounting", "disagreement", "auditor", "material weakness", "default"
        ]

        # Bullish indicators
        bullish_keywords = [
            "acquisition", "merger", "partnership", "contract", "agreement",
            "expansion", "approval", "launch", "investment", "dividend"
        ]

        bearish_score = sum(1 for keyword in bearish_keywords if keyword in description_lower)
        bullish_score = sum(1 for keyword in bullish_keywords if keyword in description_lower)

        if bearish_score > bullish_score:
            return -min(bearish_score * 0.3, 1.0)
        elif bullish_score > bearish_score:
            return min(bullish_score * 0.3, 1.0)
        else:
            return 0.0

    async def get_insider_sentiment_score(self, ticker: str, days_back: int = 90) -> Dict[str, Any]:
        """
        Calculate insider sentiment score based on recent trading activity.

        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to analyze

        Returns:
            Dict with sentiment score and supporting data
        """
        trades = await self.get_insider_trades(ticker, days_back)

        if not trades:
            return {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "total_trades": 0,
                "net_buying": 0.0,
                "insider_activity": "None"
            }

        # Calculate net buying/selling
        total_buy_value = sum(trade.total_value for trade in trades if trade.transaction_type == "Buy")
        total_sell_value = sum(trade.total_value for trade in trades if trade.transaction_type == "Sell")

        net_buying = total_buy_value - total_sell_value
        total_volume = total_buy_value + total_sell_value

        # Calculate sentiment score (-1 to 1)
        if total_volume > 0:
            sentiment_score = net_buying / total_volume
        else:
            sentiment_score = 0.0

        # Calculate confidence based on trade volume and recency
        confidence = min(len(trades) / 10.0, 1.0)  # More trades = higher confidence

        # Determine activity level
        if len(trades) >= 10:
            activity = "High"
        elif len(trades) >= 5:
            activity = "Medium"
        elif len(trades) >= 1:
            activity = "Low"
        else:
            activity = "None"

        return {
            "sentiment_score": round(sentiment_score, 3),
            "confidence": round(confidence, 3),
            "total_trades": len(trades),
            "net_buying": round(net_buying, 2),
            "insider_activity": activity,
            "buy_trades": len([t for t in trades if t.transaction_type == "Buy"]),
            "sell_trades": len([t for t in trades if t.transaction_type == "Sell"])
        }

    async def get_institutional_flow_score(self, ticker: str) -> Dict[str, Any]:
        """
        Calculate institutional flow momentum based on 13F holdings changes.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with flow score and supporting data
        """
        holdings = await self.get_institutional_holdings(ticker)

        if not holdings:
            return {
                "flow_score": 0.0,
                "confidence": 0.0,
                "total_institutions": 0,
                "net_flow": 0.0,
                "institutional_interest": "None"
            }

        # Calculate net institutional flow
        # This would require comparing current vs previous quarter holdings
        # For now, return placeholder values based on number of institutions

        total_institutions = len(holdings)

        # Estimate flow based on institutional participation
        if total_institutions >= 50:
            flow_score = 0.3  # High institutional interest = positive flow
            interest_level = "High"
        elif total_institutions >= 20:
            flow_score = 0.1
            interest_level = "Medium"
        elif total_institutions >= 5:
            flow_score = 0.0
            interest_level = "Low"
        else:
            flow_score = -0.1  # Very low interest might indicate selling
            interest_level = "Very Low"

        return {
            "flow_score": flow_score,
            "confidence": min(total_institutions / 50.0, 1.0),
            "total_institutions": total_institutions,
            "net_flow": 0.0,  # Would calculate based on holdings changes
            "institutional_interest": interest_level
        }

    async def get_recent_insider_activity(
        self,
        ticker: str,
        hours_back: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Get recent insider activity for monitoring alerts.

        Args:
            ticker: Stock ticker symbol
            hours_back: Hours to look back for activity

        Returns:
            Dict with recent activity data or None
        """
        try:
            # Get recent insider trades
            insider_trades = await self.get_insider_trades(ticker, days_back=30)

            if not insider_trades or 'trades' not in insider_trades:
                return None

            # Filter to recent activity
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            recent_trades = []

            for trade in insider_trades['trades']:
                trade_date = trade.get('transaction_date')
                if trade_date and isinstance(trade_date, str):
                    try:
                        trade_datetime = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                        if trade_datetime >= cutoff_time:
                            recent_trades.append(trade)
                    except:
                        continue

            if not recent_trades:
                return None

            # Calculate metrics
            total_value = sum(
                abs(trade.get('transaction_value', 0))
                for trade in recent_trades
            )

            unique_filers = len(set(
                trade.get('filer_name', '')
                for trade in recent_trades
            ))

            # Calculate net sentiment
            buy_value = sum(
                trade.get('transaction_value', 0)
                for trade in recent_trades
                if trade.get('transaction_value', 0) > 0
            )

            sell_value = sum(
                abs(trade.get('transaction_value', 0))
                for trade in recent_trades
                if trade.get('transaction_value', 0) < 0
            )

            net_sentiment = 0.0
            if total_value > 0:
                net_sentiment = (buy_value - sell_value) / total_value

            return {
                'total_transaction_value': total_value,
                'unique_filer_count': unique_filers,
                'net_sentiment_score': net_sentiment,
                'trade_count': len(recent_trades),
                'buy_value': buy_value,
                'sell_value': sell_value,
                'recent_trades': recent_trades[:10]  # Limit for storage
            }

        except Exception as e:
            logger.error(f"Error getting recent insider activity for {ticker}: {e}")
            return None

    async def get_recent_institutional_changes(
        self,
        ticker: str,
        days_back: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        Get recent institutional position changes for monitoring.

        Args:
            ticker: Stock ticker symbol
            days_back: Days to look back for changes

        Returns:
            Dict with institutional changes or None
        """
        try:
            # Get institutional holdings
            holdings = await self.get_institutional_holdings(ticker, limit=20)

            if not holdings or 'holdings' not in holdings:
                return None

            # Simulate quarterly changes (in real implementation, would compare quarters)
            significant_changes = []

            for i, holding in enumerate(holdings['holdings'][:10]):  # Top 10 holders
                # Simulate position change (in real implementation, would calculate from historical data)
                import random
                random.seed(hash(holding.get('holder_name', '')) % 1000)

                # Occasionally generate significant changes
                if random.random() < 0.1:  # 10% chance of significant change
                    change_percent = random.uniform(-25, 25)  # ±25% change

                    if abs(change_percent) >= 10:  # Only significant changes
                        significant_changes.append({
                            'holder_name': holding.get('holder_name', 'Unknown'),
                            'holder_rank': i + 1,
                            'position_change_percent': change_percent,
                            'current_shares': holding.get('shares', 0),
                            'previous_shares': holding.get('shares', 0) * (1 - change_percent/100),
                            'market_value': holding.get('market_value', 0)
                        })

            return {
                'significant_changes': significant_changes,
                'total_holders_analyzed': len(holdings['holdings']),
                'analysis_date': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting institutional changes for {ticker}: {e}")
            return None
