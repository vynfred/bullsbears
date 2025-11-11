"""
Firebase Integration for BullsBears
Handles real-time updates to Firebase for the frontend
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


class FirebaseClient:
    """Firebase Realtime Database client for BullsBears"""
    
    def __init__(self):
        self.project_id = os.getenv('FIREBASE_PROJECT_ID', 'bullsbears-default')
        self.database_url = os.getenv('FIREBASE_DATABASE_URL', f'https://{self.project_id}-default-rtdb.firebaseio.com')
        self.api_key = os.getenv('FIREBASE_API_KEY')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Firebase paths
        self.pulse_path = "/pulse/latest"
        self.picks_path = "/picks"
        self.stats_path = "/stats"
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def update_data(self, path: str, data: Dict[str, Any]) -> bool:
        """Update data at Firebase path"""
        try:
            await self.connect()
            
            url = f"{self.database_url}{path}.json"
            if self.api_key:
                url += f"?auth={self.api_key}"
            
            async with self.session.put(url, json=data) as response:
                if response.status == 200:
                    logger.debug(f"Firebase update successful: {path}")
                    return True
                else:
                    logger.error(f"Firebase update failed: {response.status} - {path}")
                    return False
                    
        except Exception as e:
            logger.error(f"Firebase update error: {str(e)}")
            return False
    
    async def push_data(self, path: str, data: Dict[str, Any]) -> Optional[str]:
        """Push new data to Firebase path (generates unique key)"""
        try:
            await self.connect()
            
            url = f"{self.database_url}{path}.json"
            if self.api_key:
                url += f"?auth={self.api_key}"
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    key = result.get('name')
                    logger.debug(f"Firebase push successful: {path} -> {key}")
                    return key
                else:
                    logger.error(f"Firebase push failed: {response.status} - {path}")
                    return None
                    
        except Exception as e:
            logger.error(f"Firebase push error: {str(e)}")
            return None


# Global Firebase client
_firebase_client: Optional[FirebaseClient] = None


async def get_firebase_client() -> FirebaseClient:
    """Get global Firebase client instance"""
    global _firebase_client
    
    if _firebase_client is None:
        _firebase_client = FirebaseClient()
    
    return _firebase_client


async def update_pulse_feed(pulse_data: Dict[str, Any]) -> bool:
    """
    Update the Firebase pulse/latest feed with new picks
    This is what the frontend reads for real-time updates
    """
    try:
        client = await get_firebase_client()
        
        # Structure the pulse data for frontend consumption
        formatted_data = {
            "timestamp": pulse_data.get("timestamp", datetime.now().isoformat()),
            "bullish_picks": pulse_data.get("moon", []),
            "bearish_picks": pulse_data.get("rug", []),
            "hit_rate_7d": pulse_data.get("hit_rate_7d", 68.0),
            "market_condition": pulse_data.get("market_condition", "normal"),
            "total_picks": len(pulse_data.get("moon", [])) + len(pulse_data.get("rug", [])),
            "scan_completed": True,
            "next_scan": "tomorrow_0830"
        }
        
        async with client as fb:
            success = await fb.update_data("/pulse/latest", formatted_data)
            
            if success:
                logger.info("🔥 Firebase pulse feed updated successfully")
                
                # Also update historical picks
                await update_historical_picks(pulse_data)
                
                return True
            else:
                logger.error("Failed to update Firebase pulse feed")
                return False
                
    except Exception as e:
        logger.error(f"Firebase pulse update failed: {str(e)}")
        return False


async def update_historical_picks(pulse_data: Dict[str, Any]) -> bool:
    """Update historical picks for performance tracking"""
    try:
        client = await get_firebase_client()
        
        # Create historical record
        historical_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": pulse_data.get("timestamp", datetime.now().isoformat()),
            "bullish_picks": pulse_data.get("moon", []),
            "bearish_picks": pulse_data.get("rug", []),
            "market_condition": pulse_data.get("market_condition", "normal"),
            "outcomes": {}  # Will be updated later when outcomes are determined
        }
        
        # Push to historical picks
        date_key = datetime.now().strftime("%Y%m%d")
        path = f"/picks/historical/{date_key}"
        
        async with client as fb:
            success = await fb.update_data(path, historical_data)
            
            if success:
                logger.info("📚 Historical picks updated")
                return True
            else:
                logger.error("Failed to update historical picks")
                return False
                
    except Exception as e:
        logger.error(f"Historical picks update failed: {str(e)}")
        return False


async def update_performance_stats(stats_data: Dict[str, Any]) -> bool:
    """Update performance statistics in Firebase"""
    try:
        client = await get_firebase_client()
        
        # Format stats for frontend
        formatted_stats = {
            "accuracy_7d": stats_data.get("accuracy_7d", 68.0),
            "accuracy_30d": stats_data.get("accuracy_30d", 65.0),
            "total_picks": stats_data.get("total_picks", 0),
            "win_rate": stats_data.get("win_rate", 0.0),
            "avg_confidence": stats_data.get("avg_confidence", 75.0),
            "last_updated": datetime.now().isoformat()
        }
        
        async with client as fb:
            success = await fb.update_data("/stats/performance", formatted_stats)
            
            if success:
                logger.info("📊 Performance stats updated")
                return True
            else:
                logger.error("Failed to update performance stats")
                return False
                
    except Exception as e:
        logger.error(f"Performance stats update failed: {str(e)}")
        return False


async def update_agent_status(agent_data: Dict[str, Any]) -> bool:
    """Update agent system status in Firebase"""
    try:
        client = await get_firebase_client()
        
        # Format agent status
        status_data = {
            "last_scan": datetime.now().isoformat(),
            "agents_healthy": agent_data.get("ollama_healthy", False),
            "total_agents": len(agent_data.get("agents", {})),
            "healthy_agents": sum(1 for agent in agent_data.get("agents", {}).values() if agent.get("healthy")),
            "next_scan": "tomorrow_0830",
            "system_status": "healthy" if agent_data.get("ollama_healthy") else "degraded"
        }
        
        async with client as fb:
            success = await fb.update_data("/system/agent_status", status_data)
            
            if success:
                logger.info("🤖 Agent status updated")
                return True
            else:
                logger.error("Failed to update agent status")
                return False
                
    except Exception as e:
        logger.error(f"Agent status update failed: {str(e)}")
        return False


async def close_firebase():
    """Close Firebase client"""
    global _firebase_client
    
    if _firebase_client:
        await _firebase_client.close()
        _firebase_client = None
