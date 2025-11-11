"""
Historical Data Model for BullsBears System
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

@dataclass
class HistoricalData:
    """Historical stock data model"""
    symbol: str
    date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None
    
    def __post_init__(self):
        """Convert float values to Decimal for precision"""
        if isinstance(self.open_price, float):
            self.open_price = Decimal(str(self.open_price))
        if isinstance(self.high_price, float):
            self.high_price = Decimal(str(self.high_price))
        if isinstance(self.low_price, float):
            self.low_price = Decimal(str(self.low_price))
        if isinstance(self.close_price, float):
            self.close_price = Decimal(str(self.close_price))
        if self.adjusted_close is not None and isinstance(self.adjusted_close, float):
            self.adjusted_close = Decimal(str(self.adjusted_close))
