"""
Economic Events Analyzer
Integrates economic calendar data into ML predictions
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class EventImpact(Enum):
    """Economic event impact levels"""
    HIGH = "HIGH"           # CPI, Fed Rates, Jobs Report
    MEDIUM = "MEDIUM"       # PMI, Retail Sales, GDP
    LOW = "LOW"             # Regional data, minor indicators


class SectorSensitivity(Enum):
    """How different sectors react to economic events"""
    RATE_SENSITIVE = "RATE_SENSITIVE"       # Tech, Growth stocks
    RATE_POSITIVE = "RATE_POSITIVE"         # Banks, Financials
    INFLATION_SENSITIVE = "INFLATION_SENSITIVE"  # Consumer, Materials
    DEFENSIVE = "DEFENSIVE"                 # Utilities, REITs
    CYCLICAL = "CYCLICAL"                   # Industrials, Energy


@dataclass
class EconomicEvent:
    """Economic calendar event"""
    name: str
    date: datetime
    impact: EventImpact
    expected_value: Optional[float]
    previous_value: Optional[float]
    actual_value: Optional[float]
    currency: str
    sector_impacts: Dict[SectorSensitivity, float]  # -1 to 1 impact score


@dataclass
class EventAnalysis:
    """Analysis of how economic events affect a stock"""
    pre_event_risk_score: float         # Risk before event (0-100)
    post_event_catalyst_score: float    # Catalyst potential after event (0-100)
    volatility_multiplier: float        # Expected volatility increase (1.0-3.0)
    sector_alignment: float             # How aligned stock is with event impact (-1 to 1)
    key_events: List[str]               # Upcoming events affecting this stock
    reasoning: List[str]                # Why these events matter


class EconomicEventsAnalyzer:
    """
    Analyzes economic calendar events and their impact on individual stocks
    """
    
    def __init__(self):
        # Economic event definitions
        self.high_impact_events = {
            'CPI': {'inflation_sensitive': -0.8, 'rate_sensitive': -0.6, 'rate_positive': 0.4},
            'Federal Funds Rate': {'rate_sensitive': -0.9, 'rate_positive': 0.8, 'defensive': 0.3},
            'Non-Farm Payrolls': {'cyclical': 0.7, 'defensive': -0.3, 'rate_sensitive': -0.4},
            'GDP': {'cyclical': 0.8, 'defensive': -0.2, 'inflation_sensitive': 0.3},
            'FOMC Meeting': {'rate_sensitive': -0.7, 'rate_positive': 0.6, 'defensive': 0.2}
        }
        
        self.medium_impact_events = {
            'PMI Manufacturing': {'cyclical': 0.6, 'defensive': -0.2},
            'Retail Sales': {'inflation_sensitive': 0.5, 'cyclical': 0.4},
            'Consumer Confidence': {'inflation_sensitive': 0.4, 'cyclical': 0.3},
            'PPI': {'inflation_sensitive': -0.5, 'cyclical': -0.3}
        }
        
        # Sector classifications (you'd map actual stocks to these)
        self.sector_mapping = {
            'AAPL': SectorSensitivity.RATE_SENSITIVE,
            'TSLA': SectorSensitivity.RATE_SENSITIVE,
            'NVDA': SectorSensitivity.RATE_SENSITIVE,
            'MSFT': SectorSensitivity.RATE_SENSITIVE,
            'JPM': SectorSensitivity.RATE_POSITIVE,
            'BAC': SectorSensitivity.RATE_POSITIVE,
            'WMT': SectorSensitivity.INFLATION_SENSITIVE,
            'PG': SectorSensitivity.INFLATION_SENSITIVE,
            'XOM': SectorSensitivity.CYCLICAL,
            'CAT': SectorSensitivity.CYCLICAL
        }
    
    async def analyze_economic_impact(self, symbol: str, upcoming_events: List[EconomicEvent]) -> EventAnalysis:
        """
        Analyze how upcoming economic events will impact a specific stock
        
        Args:
            symbol: Stock symbol
            upcoming_events: List of upcoming economic events (next 7 days)
            
        Returns:
            EventAnalysis with impact scores and reasoning
        """
        try:
            # Get stock's sector sensitivity
            sector = self.sector_mapping.get(symbol, SectorSensitivity.CYCLICAL)
            
            # Analyze each upcoming event
            pre_event_risk = 0.0
            post_event_catalyst = 0.0
            volatility_multiplier = 1.0
            key_events = []
            reasoning = []
            
            for event in upcoming_events:
                impact_score = self._calculate_event_impact(event, sector)
                
                if abs(impact_score) > 0.3:  # Significant impact
                    key_events.append(f"{event.name} on {event.date.strftime('%m/%d')}")
                    
                    # Pre-event risk (uncertainty)
                    if event.impact == EventImpact.HIGH:
                        pre_event_risk += 30 * abs(impact_score)
                        volatility_multiplier += 0.5
                    elif event.impact == EventImpact.MEDIUM:
                        pre_event_risk += 15 * abs(impact_score)
                        volatility_multiplier += 0.2
                    
                    # Post-event catalyst (if positive impact expected)
                    if impact_score > 0:
                        post_event_catalyst += 40 * impact_score
                        reasoning.append(f"• {event.name} likely positive for {sector.value.lower()} stocks")
                    else:
                        reasoning.append(f"• {event.name} poses risk for {sector.value.lower()} stocks")
            
            # Calculate sector alignment
            sector_alignment = self._calculate_sector_alignment(upcoming_events, sector)
            
            # Add economic context reasoning
            if len(key_events) > 0:
                reasoning.append(f"• {len(key_events)} major economic events this week")
                reasoning.append("• Consider position sizing around event volatility")
            
            return EventAnalysis(
                pre_event_risk_score=min(100, pre_event_risk),
                post_event_catalyst_score=min(100, post_event_catalyst),
                volatility_multiplier=min(3.0, volatility_multiplier),
                sector_alignment=sector_alignment,
                key_events=key_events,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Error analyzing economic impact for {symbol}: {e}")
            return self._get_default_analysis()
    
    def _calculate_event_impact(self, event: EconomicEvent, sector: SectorSensitivity) -> float:
        """Calculate how much an event impacts a specific sector"""
        
        # Get base impact from event type
        if event.name in self.high_impact_events:
            sector_impacts = self.high_impact_events[event.name]
        elif event.name in self.medium_impact_events:
            sector_impacts = self.medium_impact_events[event.name]
        else:
            return 0.0  # Unknown event
        
        # Get sector-specific impact
        sector_key = sector.value.lower()
        base_impact = sector_impacts.get(sector_key, 0.0)
        
        # Adjust based on expected vs previous values (if available)
        if event.expected_value and event.previous_value:
            surprise_factor = (event.expected_value - event.previous_value) / event.previous_value
            base_impact *= (1 + surprise_factor)
        
        return base_impact
    
    def _calculate_sector_alignment(self, events: List[EconomicEvent], sector: SectorSensitivity) -> float:
        """Calculate overall sector alignment with upcoming events"""
        
        total_impact = 0.0
        event_count = 0
        
        for event in events:
            impact = self._calculate_event_impact(event, sector)
            if abs(impact) > 0.1:  # Only count meaningful impacts
                total_impact += impact
                event_count += 1
        
        if event_count == 0:
            return 0.0
        
        return total_impact / event_count
    
    def _get_default_analysis(self) -> EventAnalysis:
        """Default analysis when data unavailable"""
        return EventAnalysis(
            pre_event_risk_score=10.0,
            post_event_catalyst_score=10.0,
            volatility_multiplier=1.1,
            sector_alignment=0.0,
            key_events=[],
            reasoning=["• No major economic events identified this week"]
        )
    
    async def get_upcoming_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """
        Get upcoming economic events from calendar API
        
        This would integrate with:
        - Alpha Vantage Economic Calendar
        - Trading Economics API
        - Federal Reserve Economic Data (FRED)
        - Finnhub Economic Calendar
        """
        try:
            # Mock data for now - replace with actual API calls
            upcoming_events = [
                EconomicEvent(
                    name="CPI",
                    date=datetime.now() + timedelta(days=2),
                    impact=EventImpact.HIGH,
                    expected_value=3.2,
                    previous_value=3.4,
                    actual_value=None,
                    currency="USD",
                    sector_impacts=self.high_impact_events['CPI']
                ),
                EconomicEvent(
                    name="Federal Funds Rate",
                    date=datetime.now() + timedelta(days=5),
                    impact=EventImpact.HIGH,
                    expected_value=5.25,
                    previous_value=5.00,
                    actual_value=None,
                    currency="USD",
                    sector_impacts=self.high_impact_events['Federal Funds Rate']
                )
            ]
            
            return upcoming_events
            
        except Exception as e:
            logger.error(f"Error fetching economic events: {e}")
            return []


# Global instance
_economic_analyzer = None

async def get_economic_events_analyzer() -> EconomicEventsAnalyzer:
    """Get global economic events analyzer instance"""
    global _economic_analyzer
    if _economic_analyzer is None:
        _economic_analyzer = EconomicEventsAnalyzer()
    return _economic_analyzer
