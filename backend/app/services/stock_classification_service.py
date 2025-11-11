#!/usr/bin/env python3
"""
Stock Classification Service - Tiered Stock Management
Manages the 5-tier stock classification system: ALL → ACTIVE → QUALIFIED → SHORT_LIST → PICKS
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from ..core.database import get_database
from ..models.stock_classifications import StockClassification

logger = logging.getLogger(__name__)

@dataclass
class TierCriteria:
    """Criteria for each tier classification"""
    min_price: float = 0.0
    min_volume: int = 0
    exclude_penny_stocks: bool = False
    exclude_recent_ipos: bool = False
    exclude_delisting_warnings: bool = False

class StockClassificationService:
    """
    Manages the tiered stock classification system
    
    Tiers:
    - ALL (6,960): Complete NASDAQ stock list
    - ACTIVE (~3,000): Viable investment candidates
    - QUALIFIED (~50-500): Showing momentum signs
    - SHORT_LIST (max 80): Daily candidate pool
    - PICKS (max 6): Final daily recommendations
    """
    
    def __init__(self):
        self.db = None
        self.initialized = False
        
        # Tier criteria
        self.tier_criteria = {
            'ACTIVE': TierCriteria(
                min_price=1.25,
                min_volume=100000,
                exclude_penny_stocks=True,
                exclude_recent_ipos=True,
                exclude_delisting_warnings=True
            ),
            'QUALIFIED': TierCriteria(
                min_price=1.25,
                min_volume=100000
            )
        }
        
    async def initialize(self):
        """Initialize the service"""
        if self.initialized:
            return
            
        try:
            self.db = await get_database()
            self.initialized = True
            logger.info("✅ Stock Classification Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Stock Classification Service: {e}")
            raise
    
    async def get_tier_stocks(self, tier: str) -> List[Dict[str, Any]]:
        """
        Get all stocks in a specific tier
        
        Args:
            tier: 'ALL', 'ACTIVE', 'QUALIFIED', 'SHORT_LIST', 'PICKS'
            
        Returns:
            List of stock data dictionaries
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Simplified query without historical_data table for now
            query = """
                SELECT sc.*,
                       sc.price as current_price,
                       sc.daily_volume as current_volume
                FROM stock_classifications sc
                WHERE sc.current_tier = $1
                ORDER BY sc.updated_at DESC
            """
            
            result = await self.db.fetch(query, tier)
            
            stocks = []
            for row in result:
                stock_data = {
                    'symbol': row['symbol'],
                    'current_tier': row['current_tier'],
                    'price': float(row['current_price']) if row['current_price'] else 0.0,
                    'market_cap': row['market_cap'],
                    'daily_volume': row['current_volume'],
                    'last_qualified_date': row['last_qualified_date'],
                    'qualified_days_count': row['qualified_days_count'],
                    'selection_fatigue_count': row['selection_fatigue_count'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                stocks.append(stock_data)
            
            logger.info(f"Retrieved {len(stocks)} stocks from {tier} tier")
            return stocks
            
        except Exception as e:
            logger.error(f"Failed to get {tier} tier stocks: {e}")
            raise
    
    async def update_stock_tier(self, symbol: str, new_tier: str, reasoning: str = None) -> bool:
        """
        Update a stock's tier classification
        
        Args:
            symbol: Stock symbol
            new_tier: New tier classification
            reasoning: Optional reasoning for the change
            
        Returns:
            True if successful
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Get current stock data
            current_stock = await self.db.fetchrow(
                "SELECT * FROM stock_classifications WHERE symbol = $1", symbol
            )
            
            if not current_stock:
                logger.warning(f"Stock {symbol} not found in classifications")
                return False
            
            # Update tier and timestamp
            await self.db.execute("""
                UPDATE stock_classifications
                SET current_tier = $1::VARCHAR,
                    updated_at = CURRENT_TIMESTAMP,
                    qualified_days_count = CASE
                        WHEN $1::VARCHAR = 'QUALIFIED' THEN qualified_days_count + 1
                        ELSE 0
                    END,
                    last_qualified_date = CASE
                        WHEN $1::VARCHAR = 'QUALIFIED' THEN CURRENT_DATE
                        ELSE last_qualified_date
                    END
                WHERE symbol = $2::VARCHAR
            """, new_tier, symbol)
            
            # Log tier movement
            await self._log_tier_movement(symbol, current_stock['current_tier'], new_tier, reasoning)
            
            logger.info(f"Updated {symbol}: {current_stock['current_tier']} → {new_tier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update tier for {symbol}: {e}")
            return False
    
    async def run_monthly_active_review(self) -> Dict[str, int]:
        """
        Run monthly review to update ACTIVE tier
        Filters ALL tier stocks based on ACTIVE criteria
        
        Returns:
            Statistics about tier movements
        """
        logger.info("Starting monthly ACTIVE tier review...")
        
        try:
            # Get all stocks currently in ALL tier
            all_stocks = await self.get_tier_stocks('ALL')
            
            stats = {
                'reviewed': len(all_stocks),
                'promoted_to_active': 0,
                'demoted_from_active': 0,
                'remained_active': 0
            }
            
            criteria = self.tier_criteria['ACTIVE']
            
            for stock in all_stocks:
                symbol = stock['symbol']
                price = stock['price']
                volume = stock['daily_volume']
                
                # Check if stock meets ACTIVE criteria
                meets_criteria = (
                    price >= criteria.min_price and
                    volume >= criteria.min_volume and
                    not self._is_penny_stock(symbol) and
                    not self._is_recent_ipo(symbol) and
                    not self._has_delisting_warning(symbol)
                )
                
                current_tier = stock['current_tier']
                
                if meets_criteria and current_tier == 'ALL':
                    await self.update_stock_tier(symbol, 'ACTIVE', 'Monthly review - meets criteria')
                    stats['promoted_to_active'] += 1
                elif not meets_criteria and current_tier == 'ACTIVE':
                    await self.update_stock_tier(symbol, 'ALL', 'Monthly review - no longer meets criteria')
                    stats['demoted_from_active'] += 1
                elif meets_criteria and current_tier == 'ACTIVE':
                    stats['remained_active'] += 1
            
            logger.info(f"✅ Monthly ACTIVE review complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Monthly ACTIVE review failed: {e}")
            raise
    
    async def run_daily_qualified_review(self) -> Dict[str, int]:
        """
        Run daily review to update QUALIFIED tier
        Remove stocks that haven't shown momentum for 3+ days
        
        Returns:
            Statistics about tier movements
        """
        logger.info("Starting daily QUALIFIED tier review...")
        
        try:
            # Get stocks that have been QUALIFIED for 3+ days without momentum
            cutoff_date = date.today() - timedelta(days=3)
            
            stale_qualified = await self.db.fetch("""
                SELECT symbol, current_tier, last_qualified_date, qualified_days_count
                FROM stock_classifications 
                WHERE current_tier = 'QUALIFIED' 
                AND last_qualified_date < $1
            """, cutoff_date)
            
            stats = {
                'reviewed': len(stale_qualified),
                'demoted_to_active': 0
            }
            
            for stock in stale_qualified:
                symbol = stock['symbol']
                
                # TODO: Check if stock still shows momentum signs
                # For now, demote stocks that have been QUALIFIED for 3+ days
                await self.update_stock_tier(symbol, 'ACTIVE', 'Daily review - no momentum for 3+ days')
                stats['demoted_to_active'] += 1
            
            logger.info(f"✅ Daily QUALIFIED review complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Daily QUALIFIED review failed: {e}")
            raise
    
    async def increment_selection_fatigue(self, symbol: str):
        """Increment selection fatigue count for a stock"""
        try:
            await self.db.execute("""
                UPDATE stock_classifications 
                SET selection_fatigue_count = selection_fatigue_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE symbol = $1
            """, symbol)
            
            logger.debug(f"Incremented selection fatigue for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to increment selection fatigue for {symbol}: {e}")
    
    async def get_tier_statistics(self) -> Dict[str, int]:
        """Get current tier distribution statistics"""
        try:
            result = await self.db.fetch("""
                SELECT current_tier, COUNT(*) as count
                FROM stock_classifications
                GROUP BY current_tier
                ORDER BY 
                    CASE current_tier 
                        WHEN 'PICKS' THEN 5
                        WHEN 'SHORT_LIST' THEN 4
                        WHEN 'QUALIFIED' THEN 3
                        WHEN 'ACTIVE' THEN 2
                        WHEN 'ALL' THEN 1
                    END DESC
            """)
            
            stats = {}
            for row in result:
                stats[row['current_tier']] = row['count']
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get tier statistics: {e}")
            return {}
    
    async def _log_tier_movement(self, symbol: str, from_tier: str, to_tier: str, reasoning: str = None):
        """Log tier movement for analytics"""
        try:
            # TODO: Implement tier movement logging table
            logger.info(f"Tier movement: {symbol} {from_tier} → {to_tier} ({reasoning})")
        except Exception as e:
            logger.error(f"Failed to log tier movement: {e}")
    
    def _is_penny_stock(self, symbol: str) -> bool:
        """Check if stock is a penny stock"""
        # TODO: Implement penny stock detection logic
        return False
    
    def _is_recent_ipo(self, symbol: str) -> bool:
        """Check if stock is a recent IPO (< 6 months)"""
        # TODO: Implement recent IPO detection logic
        return False
    
    def _has_delisting_warning(self, symbol: str) -> bool:
        """Check if stock has delisting warnings"""
        # TODO: Implement delisting warning detection logic
        return False
