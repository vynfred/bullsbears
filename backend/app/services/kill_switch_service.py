#!/usr/bin/env python3
"""
Kill Switch Service - Market Condition Override
VIX >35 AND SPY <-2% = Block all pick generation
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from ..core.database import get_asyncpg_pool

logger = logging.getLogger(__name__)

class KillSwitchService:
    """
    Kill Switch Service - Market condition monitoring
    Blocks pick generation when VIX >35 AND SPY <-2%
    """
    
    def __init__(self):
        self.db = None
        self.initialized = False
        
        # Kill switch thresholds from roadmap
        self.vix_threshold = 35.0
        self.spy_threshold = -2.0
    
    async def initialize(self):
        """Initialize database connection"""
        if not self.initialized:
            self.db = await get_asyncpg_pool()
            self.initialized = True
    
    async def check_market_conditions(self) -> bool:
        """
        Check if kill switch should be activated
        Returns True if market conditions warrant blocking picks
        """
        await self.initialize()
        
        try:
            # Get current market data
            market_data = await self.get_current_market_data()
            
            vix_level = market_data.get('vix', 0)
            spy_change = market_data.get('spy_change_percent', 0)
            
            # Kill switch logic: VIX >35 AND SPY <-2%
            kill_switch_active = vix_level > self.vix_threshold and spy_change < self.spy_threshold
            
            if kill_switch_active:
                logger.warning(f"🛑 KILL SWITCH ACTIVATED: VIX {vix_level:.1f} (>{self.vix_threshold}) AND SPY {spy_change:.1f}% (<{self.spy_threshold}%)")
                
                # Log kill switch activation
                await self.log_kill_switch_activation(vix_level, spy_change)
            else:
                logger.info(f"✅ Market conditions normal: VIX {vix_level:.1f}, SPY {spy_change:.1f}%")
            
            return kill_switch_active
            
        except Exception as e:
            logger.error(f"❌ Kill switch check failed: {e}")
            # Fail safe: activate kill switch if we can't check conditions
            return True
    
    async def get_current_market_data(self) -> Dict[str, float]:
        """Get current VIX and SPY data from database or API"""
        try:
            # Try to get from database first
            market_data = await self.db.fetchrow("""
                SELECT 
                    (SELECT price FROM market_data WHERE symbol = 'VIX' ORDER BY timestamp DESC LIMIT 1) as vix,
                    (SELECT change_percent FROM market_data WHERE symbol = 'SPY' ORDER BY timestamp DESC LIMIT 1) as spy_change_percent
            """)
            
            if market_data and market_data['vix'] and market_data['spy_change_percent']:
                return {
                    'vix': float(market_data['vix']),
                    'spy_change_percent': float(market_data['spy_change_percent'])
                }
            
            # Fallback: Get from FMP API
            return await self.get_market_data_from_api()
            
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {'vix': 0, 'spy_change_percent': 0}
    
    async def get_market_data_from_api(self) -> Dict[str, float]:
        """Fallback: Get market data from FMP API"""
        try:
            from .fmp_data_ingestion import FMPDataIngestionService
            fmp_service = FMPDataIngestionService()
            
            # Get VIX and SPY data
            vix_data = await fmp_service.get_real_time_quote('VIX')
            spy_data = await fmp_service.get_real_time_quote('SPY')
            
            return {
                'vix': float(vix_data.get('price', 0)),
                'spy_change_percent': float(spy_data.get('changesPercentage', 0))
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get market data from API: {e}")
            return {'vix': 0, 'spy_change_percent': 0}
    
    async def log_kill_switch_activation(self, vix_level: float, spy_change: float):
        """Log kill switch activation to database"""
        try:
            await self.db.execute("""
                INSERT INTO kill_switch_log (vix_level, spy_change_percent, activated_at, reason)
                VALUES ($1, $2, CURRENT_TIMESTAMP, $3)
            """, vix_level, spy_change, f"VIX {vix_level:.1f} >35 AND SPY {spy_change:.1f}% <-2%")
            
        except Exception as e:
            logger.error(f"❌ Failed to log kill switch activation: {e}")
