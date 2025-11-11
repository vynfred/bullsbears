"""
BullsBears Data Flow Manager - Core Pipeline Orchestrator
Manages the complete data pipeline from FMP ingestion to agent processing
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time

from ..core.database import get_database
from ..models.stock_classifications import StockClassification
from ..models.historical_data import HistoricalData
from .fmp_data_ingestion import FMPDataIngestion
from .stock_classification_service import StockClassificationService
from .agent_manager import AgentManager
from .kill_switch_service import KillSwitchService

logger = logging.getLogger(__name__)


class DataFlowManager:
    """
    Core Data Flow Orchestrator for BullsBears AI System
    
    Manages the complete pipeline:
    1. Weekly: FMP data refresh + ALL → ACTIVE classification
    2. Daily: ACTIVE updates + Agent pipeline execution
    3. Real-time: Price updates during market hours
    """
    
    def __init__(self):
        self.fmp_service = FMPDataIngestion()
        self.classification_service = StockClassificationService()
        self.agent_manager = AgentManager()
        self.kill_switch = KillSwitchService()
        self.db_pool = None
        
    async def initialize(self):
        """Initialize all services and database connections"""
        try:
            self.db_pool = await get_database()
            await self.agent_manager.initialize()
            logger.info("DataFlowManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DataFlowManager: {e}")
            raise
    
    async def weekly_data_update(self) -> Dict[str, Any]:
        """
        WEEKLY OPERATIONS (Saturday mornings)
        - FMP update ALL tier (fresh NASDAQ universe)
        - Prefilter ALL → ACTIVE (volatility/movement criteria)
        """
        start_time = time.time()
        logger.info("🔄 Starting weekly data update")
        
        try:
            # Step 1: Update ALL tier with fresh NASDAQ data
            logger.info("Step 1: Updating ALL tier from NASDAQ universe")
            all_symbols = await self.fmp_service.get_nasdaq_universe()
            logger.info(f"Retrieved {len(all_symbols)} NASDAQ symbols")
            
            # Step 2: Update historical data for all symbols
            logger.info("Step 2: Updating historical data")
            updated_count = await self.fmp_service.update_historical_data_batch(
                symbols=all_symbols,
                days_back=7  # Weekly update - just get latest week
            )
            
            # Step 3: Classify ALL → ACTIVE based on criteria
            logger.info("Step 3: Classifying ALL → ACTIVE")
            active_count = await self.classification_service.classify_all_to_active()
            
            duration = time.time() - start_time
            result = {
                "status": "success",
                "operation": "weekly_update",
                "all_symbols": len(all_symbols),
                "updated_symbols": updated_count,
                "active_symbols": active_count,
                "duration_seconds": round(duration, 2)
            }
            
            logger.info(f"✅ Weekly update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Weekly update failed: {e}")
            raise
    
    async def daily_data_update(self) -> Dict[str, Any]:
        """
        DAILY OPERATIONS (Weekday mornings before market open)
        Phase 1: Tiered Stock Classification
        - FMP update ACTIVE tier only (price/volume updates)
        """
        start_time = time.time()
        logger.info("📊 Starting daily data update")
        
        try:
            # Step 1: Get current ACTIVE tier symbols
            active_symbols = await self.classification_service.get_active_symbols()
            logger.info(f"Updating {len(active_symbols)} ACTIVE tier symbols")
            
            # Step 2: Update ACTIVE tier with latest data
            updated_count = await self.fmp_service.update_active_tier_data(active_symbols)
            
            # Step 3: Refresh ACTIVE tier classifications
            active_count = await self.classification_service.refresh_active_tier()
            
            duration = time.time() - start_time
            result = {
                "status": "success",
                "operation": "daily_update",
                "active_symbols": len(active_symbols),
                "updated_symbols": updated_count,
                "refreshed_active": active_count,
                "duration_seconds": round(duration, 2)
            }
            
            logger.info(f"✅ Daily update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Daily update failed: {e}")
            raise
    
    async def run_daily_prescreen_full_pipeline(self) -> List[Dict[str, Any]]:
        """
        Execute prescreen pipeline (ACTIVE → SHORT_LIST)
        Uses AgentManager for the actual agent processing
        """
        logger.info("🤖 Starting prescreen pipeline (ACTIVE → SHORT_LIST)")
        
        try:
            # Use AgentManager's existing pipeline
            result = await self.agent_manager.run_daily_pipeline()
            
            # Extract SHORT_LIST from result
            short_list = result.get('shortlist', [])
            
            logger.info(f"✅ Prescreen pipeline completed: {len(short_list)} candidates")
            return short_list
            
        except Exception as e:
            logger.error(f"❌ Prescreen pipeline failed: {e}")
            raise
    
    async def run_agent_pipeline_on_shortlist(self) -> List[Dict[str, Any]]:
        """
        Execute full agent pipeline on SHORT_LIST to generate final picks
        """
        logger.info("🚀 Starting agent pipeline on SHORT_LIST")
        
        try:
            # Check kill switch first
            if await self.kill_switch.is_active():
                logger.warning("🛑 Kill switch active - no picks generated")
                return []
            
            # Use AgentManager's existing pipeline
            result = await self.agent_manager.run_daily_pipeline()
            
            # Extract final picks from result
            picks = result.get('picks', [])
            
            logger.info(f"✅ Agent pipeline completed: {len(picks)} picks generated")
            return picks
            
        except Exception as e:
            logger.error(f"❌ Agent pipeline failed: {e}")
            raise
    
    async def bootstrap_historical_data(self, days_back: int = 90) -> Dict[str, Any]:
        """
        Bootstrap database with historical data (one-time setup)
        """
        start_time = time.time()
        logger.info(f"🚀 Starting {days_back}-day historical data bootstrap")
        
        try:
            # Get NASDAQ universe
            all_symbols = await self.fmp_service.get_nasdaq_universe()
            logger.info(f"Bootstrapping {len(all_symbols)} symbols with {days_back} days of data")
            
            # Bootstrap historical data in batches
            total_updated = await self.fmp_service.bootstrap_historical_data(
                symbols=all_symbols,
                days_back=days_back
            )
            
            # Initial classification
            active_count = await self.classification_service.classify_all_to_active()
            
            duration = time.time() - start_time
            result = {
                "status": "success",
                "operation": "bootstrap",
                "total_symbols": len(all_symbols),
                "updated_symbols": total_updated,
                "active_classified": active_count,
                "days_back": days_back,
                "duration_seconds": round(duration, 2)
            }
            
            logger.info(f"✅ Bootstrap completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Bootstrap failed: {e}")
            raise
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current status of the data pipeline"""
        try:
            # Get tier counts
            tier_counts = await self.classification_service.get_tier_counts()
            
            # Get latest data timestamps
            latest_data = await self.fmp_service.get_latest_data_timestamp()
            
            # Check kill switch status
            kill_switch_active = await self.kill_switch.is_active()
            
            return {
                "tier_counts": tier_counts,
                "latest_data_timestamp": latest_data,
                "kill_switch_active": kill_switch_active,
                "status": "operational"
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.db_pool:
                await self.db_pool.close()
            logger.info("DataFlowManager cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
