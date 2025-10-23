"""
Catalyst detection system for identifying upcoming events that could impact stock prices.
Scans for earnings, economic events, FDA approvals, and other market-moving catalysts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
import yfinance as yf
from dataclasses import dataclass

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class Catalyst:
    """Data class for market catalysts."""
    symbol: str
    date: datetime
    event_type: str  # EARNINGS, FDA, ECONOMIC, MERGER, SPLIT, etc.
    description: str
    impact_score: float  # 0-10 scale
    confidence: float    # 0-1 scale
    source: str
    details: Dict[str, Any]

class CatalystDetector:
    """Service for detecting upcoming market catalysts."""
    
    def __init__(self):
        self.fmp_api_key = settings.fmp_api_key
        self.alpha_vantage_key = settings.alpha_vantage_api_key
        self.session = None
        
        # Economic events that impact markets
        self.economic_events = {
            'FOMC': {'impact': 9, 'keywords': ['fed', 'fomc', 'interest rate', 'monetary policy']},
            'CPI': {'impact': 8, 'keywords': ['cpi', 'inflation', 'consumer price']},
            'NFP': {'impact': 7, 'keywords': ['nonfarm', 'payroll', 'employment', 'jobs']},
            'GDP': {'impact': 7, 'keywords': ['gdp', 'gross domestic product', 'growth']},
            'PPI': {'impact': 6, 'keywords': ['ppi', 'producer price', 'wholesale']},
            'RETAIL': {'impact': 6, 'keywords': ['retail sales', 'consumer spending']},
            'HOUSING': {'impact': 5, 'keywords': ['housing', 'home sales', 'construction']}
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'OptionsTrader/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def detect_catalysts(self, symbol: str, days_ahead: int = 7) -> List[Catalyst]:
        """
        Detect upcoming catalysts for a specific symbol.
        
        Args:
            symbol: Stock symbol to analyze
            days_ahead: Number of days to look ahead (default 7)
            
        Returns:
            List of upcoming catalysts sorted by impact score
        """
        if not self.session:
            async with self:
                return await self._detect_all_catalysts(symbol, days_ahead)
        else:
            return await self._detect_all_catalysts(symbol, days_ahead)
    
    async def _detect_all_catalysts(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Detect all types of catalysts."""
        catalysts = []
        
        # Run all detection methods concurrently
        tasks = [
            self._detect_earnings(symbol, days_ahead),
            self._detect_economic_events(days_ahead),
            self._detect_fda_events(symbol, days_ahead),
            self._detect_corporate_actions(symbol, days_ahead),
            self._detect_analyst_events(symbol, days_ahead)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                catalysts.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Error detecting catalysts: {result}")
        
        # Sort by impact score and date
        catalysts.sort(key=lambda x: (x.impact_score, -x.date.timestamp()), reverse=True)
        
        return catalysts
    
    async def _detect_earnings(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Detect upcoming earnings announcements."""
        catalysts = []
        
        try:
            # Try FMP API first
            if self.fmp_api_key:
                catalysts.extend(await self._get_fmp_earnings(symbol, days_ahead))
            
            # Fallback to yfinance
            if not catalysts:
                catalysts.extend(await self._get_yfinance_earnings(symbol, days_ahead))
                
        except Exception as e:
            logger.warning(f"Error detecting earnings for {symbol}: {e}")
        
        return catalysts
    
    async def _get_fmp_earnings(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Get earnings data from FMP API."""
        catalysts = []
        
        try:
            url = f"https://financialmodelingprep.com/api/v3/earning_calendar"
            params = {
                'apikey': self.fmp_api_key,
                'from': datetime.now().strftime('%Y-%m-%d'),
                'to': (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data:
                        if item.get('symbol') == symbol:
                            date = datetime.strptime(item['date'], '%Y-%m-%d')
                            
                            catalyst = Catalyst(
                                symbol=symbol,
                                date=date,
                                event_type='EARNINGS',
                                description=f"Q{item.get('quarter', '?')} earnings announcement",
                                impact_score=8.0,  # Earnings are high impact
                                confidence=0.9,
                                source='FMP',
                                details={
                                    'quarter': item.get('quarter'),
                                    'year': item.get('year'),
                                    'eps_estimate': item.get('epsEstimated'),
                                    'revenue_estimate': item.get('revenueEstimated')
                                }
                            )
                            catalysts.append(catalyst)
                            
        except Exception as e:
            logger.warning(f"Error fetching FMP earnings: {e}")
        
        return catalysts
    
    async def _get_yfinance_earnings(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Get earnings data from yfinance."""
        catalysts = []
        
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            if calendar is not None and not calendar.empty:
                for date in calendar.index:
                    if isinstance(date, str):
                        earnings_date = datetime.strptime(date, '%Y-%m-%d')
                    else:
                        earnings_date = date
                    
                    if earnings_date <= datetime.now() + timedelta(days=days_ahead):
                        catalyst = Catalyst(
                            symbol=symbol,
                            date=earnings_date,
                            event_type='EARNINGS',
                            description="Earnings announcement",
                            impact_score=8.0,
                            confidence=0.8,
                            source='yfinance',
                            details={}
                        )
                        catalysts.append(catalyst)
                        
        except Exception as e:
            logger.warning(f"Error fetching yfinance earnings: {e}")
        
        return catalysts
    
    async def _detect_economic_events(self, days_ahead: int) -> List[Catalyst]:
        """Detect upcoming economic events."""
        catalysts = []
        
        try:
            # Use Alpha Vantage economic calendar if available
            if self.alpha_vantage_key:
                catalysts.extend(await self._get_alpha_vantage_economic(days_ahead))
            
            # Add known recurring events
            catalysts.extend(self._get_recurring_economic_events(days_ahead))
            
        except Exception as e:
            logger.warning(f"Error detecting economic events: {e}")
        
        return catalysts
    
    async def _get_alpha_vantage_economic(self, days_ahead: int) -> List[Catalyst]:
        """Get economic events from Alpha Vantage."""
        catalysts = []
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.alpha_vantage_key,
                'topics': 'economy,federal_reserve,inflation',
                'limit': 50
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'feed' in data:
                        for item in data['feed']:
                            # Look for economic event indicators in news
                            title = item.get('title', '').lower()
                            summary = item.get('summary', '').lower()
                            text = f"{title} {summary}"
                            
                            for event_type, config in self.economic_events.items():
                                if any(keyword in text for keyword in config['keywords']):
                                    # Try to extract date from news
                                    time_published = item.get('time_published', '')
                                    if time_published:
                                        try:
                                            date = datetime.strptime(time_published[:8], '%Y%m%d')
                                            if date <= datetime.now() + timedelta(days=days_ahead):
                                                catalyst = Catalyst(
                                                    symbol='MARKET',
                                                    date=date,
                                                    event_type='ECONOMIC',
                                                    description=f"{event_type} - {item.get('title', '')}",
                                                    impact_score=config['impact'],
                                                    confidence=0.7,
                                                    source='Alpha Vantage',
                                                    details={'url': item.get('url', '')}
                                                )
                                                catalysts.append(catalyst)
                                                break
                                        except:
                                            continue
                            
        except Exception as e:
            logger.warning(f"Error fetching Alpha Vantage economic data: {e}")
        
        return catalysts
    
    def _get_recurring_economic_events(self, days_ahead: int) -> List[Catalyst]:
        """Get known recurring economic events."""
        catalysts = []
        
        # CPI is typically released around the 10th-15th of each month
        now = datetime.now()
        for month_offset in range(2):  # Check current and next month
            target_month = now.replace(day=1) + timedelta(days=32 * month_offset)
            cpi_date = target_month.replace(day=12)  # Approximate CPI date
            
            if cpi_date <= now + timedelta(days=days_ahead) and cpi_date >= now:
                catalyst = Catalyst(
                    symbol='MARKET',
                    date=cpi_date,
                    event_type='ECONOMIC',
                    description='CPI Inflation Report',
                    impact_score=8.0,
                    confidence=0.8,
                    source='recurring',
                    details={'type': 'CPI'}
                )
                catalysts.append(catalyst)
        
        return catalysts
    
    async def _detect_fda_events(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Detect FDA approval events for biotech/pharma stocks."""
        catalysts = []
        
        # This would require specialized FDA databases
        # For now, return empty list - can be enhanced with FDA API
        
        return catalysts
    
    async def _detect_corporate_actions(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Detect corporate actions like splits, dividends, mergers."""
        catalysts = []
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Check for upcoming dividends
            dividends = ticker.dividends
            if not dividends.empty:
                last_div_date = dividends.index[-1]
                # Estimate next dividend (quarterly assumption)
                next_div_date = last_div_date + timedelta(days=90)
                
                if next_div_date <= datetime.now() + timedelta(days=days_ahead):
                    catalyst = Catalyst(
                        symbol=symbol,
                        date=next_div_date,
                        event_type='DIVIDEND',
                        description='Estimated dividend payment',
                        impact_score=3.0,
                        confidence=0.6,
                        source='yfinance',
                        details={'last_dividend': dividends.iloc[-1]}
                    )
                    catalysts.append(catalyst)
            
            # Check for stock splits (from actions)
            actions = ticker.actions
            if not actions.empty:
                recent_actions = actions[actions.index >= datetime.now() - timedelta(days=30)]
                if not recent_actions.empty:
                    for date, row in recent_actions.iterrows():
                        if row.get('Stock Splits', 0) > 0:
                            catalyst = Catalyst(
                                symbol=symbol,
                                date=date,
                                event_type='SPLIT',
                                description=f"Stock split {row['Stock Splits']}:1",
                                impact_score=6.0,
                                confidence=0.9,
                                source='yfinance',
                                details={'split_ratio': row['Stock Splits']}
                            )
                            catalysts.append(catalyst)
                            
        except Exception as e:
            logger.warning(f"Error detecting corporate actions for {symbol}: {e}")
        
        return catalysts
    
    async def _detect_analyst_events(self, symbol: str, days_ahead: int) -> List[Catalyst]:
        """Detect analyst events like upgrades, downgrades, price target changes."""
        catalysts = []
        
        # This would require specialized analyst data feeds
        # For now, return empty list - can be enhanced with analyst APIs
        
        return catalysts

# Utility function for easy usage
async def get_catalysts(symbol: str, days_ahead: int = 7) -> List[Catalyst]:
    """Convenience function to get catalysts for a symbol."""
    async with CatalystDetector() as detector:
        return await detector.detect_catalysts(symbol, days_ahead)
