"""
Simple Daily Price Tracker - Replaces Complex Real-Time Systems
Just daily closes for 30-day SHORT_LIST retrospective analysis
"""

import logging
from datetime import datetime
from typing import Dict, List

from ..services.stock_data import StockDataService
from ..models.pick_candidates import PickCandidate

logger = logging.getLogger(__name__)

class SimpleDailyTracker:
    """Simple daily price updates - no real-time complexity"""
    
    def __init__(self):
        self.stock_service = StockDataService()
    
    async def update_shortlist_prices(self, db) -> Dict:
        """Update daily closes for 75 SHORT_LIST candidates"""
        
        # Get active SHORT_LIST candidates
        candidates = db.query(PickCandidate).filter(
            PickCandidate.status == 'ACTIVE'
        ).all()
        
        results = {"updated": 0, "errors": 0}
        
        for candidate in candidates:
            try:
                # Simple daily close update
                price_data = await self.stock_service.get_daily_close(candidate.symbol)
                if price_data:
                    candidate.current_price = price_data['close']
                    candidate.last_updated = datetime.now()
                    results["updated"] += 1
            except Exception as e:
                logger.error(f"Error updating {candidate.symbol}: {e}")
                results["errors"] += 1
        
        db.commit()
        return results