"""
BullsBears Database Models – FINAL v3.3 (November 11, 2025)
All models used in the current lean pipeline.
No legacy tables. No dead code.
"""

# Core market data
from .stock import Stock, StockPrice
from .historical_data import HistoricalData

# Classification & screening
from .stock_classifications import StockClassification

# Candidate tracking & picks (current system)
from .pick_candidates import ShortListCandidate, FinalPick

# User features
from .user_preferences import UserPreferences
from .watchlist import (
    WatchlistEntry,
    WatchlistPriceHistory,
    PerformanceSummary,
    WatchlistEvent,
    WatchlistEventType,
)

# Public API – alphabetical for clarity
__all__ = [
    "FinalPick",
    "HistoricalData",
    "PerformanceSummary",
    "ShortListCandidate",
    "Stock",
    "StockClassification",
    "StockPrice",
    "UserPreferences",
    "WatchlistEntry",
    "WatchlistEvent",
    "WatchlistEventType",
    "WatchlistPriceHistory",
]