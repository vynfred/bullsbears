"""
Firebase Integration for BullsBears v5 – November 2025
Uses Firebase Admin SDK (service account) — NOT Realtime Database REST API
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import db

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    # Get service account from environment variable
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if not service_account_json:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable not set")
    
    # Parse JSON string
    service_account_dict = json.loads(service_account_json)
    
    # Initialize with credentials
    cred = credentials.Certificate(service_account_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://bullsbears-xyz-default-rtdb.firebaseio.com/'
    })
    
    # Get database reference
    database_ref = db.reference()
    
    logger.info("Firebase initialized successfully")
    
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")
    database_ref = None

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
            "bullish_picks": pulse_data.get("bullish", []),
            "bearish_picks": pulse_data.get("bearish", []),
            "hit_rate_7d": pulse_data.get("hit_rate_7d", 68.0),
            "market_condition": pulse_data.get("market_condition", "normal"),
            "total_picks": len(pulse_data.get("bullish", [])) + len(pulse_data.get("bearish", [])),
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
            "bullish_picks": pulse_data.get("bullish", []),
            "bearish_picks": pulse_data.get("bearish", []),
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

# Add this at the very bottom of the file
def update_firebase_sync(path: str, data: Dict[str, Any]):
    """Sync wrapper for your existing async functions — used by Celery tasks"""
    try:
        ref = database_ref.child(path)
        ref.set(data)
        logger.info(f"Firebase sync update: {path}")
    except Exception as e:
        logger.error(f"Firebase sync update failed: {e}")

# Keep your existing async versions for future use
# Or just call update_firebase_sync() from tasks if you want zero async hassle
