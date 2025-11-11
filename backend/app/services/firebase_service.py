"""
Firebase Realtime Database Service
Handles real-time data updates for BullsBears frontend
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
from dataclasses import asdict

logger = logging.getLogger(__name__)

class FirebaseService:
    """Firebase Realtime Database service for real-time picks updates"""
    
    def __init__(self):
        self.project_id = "603494406675"
        self.database_url = "https://bullsbears-xyz-default-rtdb.firebaseio.com"
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure session is created"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def push_picks_to_firebase(self, picks: List[Dict[str, Any]]) -> bool:
        """
        Push latest picks to Firebase Realtime Database
        """
        try:
            await self._ensure_session()
            
            # Format picks for Firebase
            firebase_data = {
                "timestamp": datetime.now().isoformat(),
                "picks": picks,
                "total_picks": len(picks),
                "bullish_count": len([p for p in picks if p.get('direction') == 'bullish']),
                "bearish_count": len([p for p in picks if p.get('direction') == 'bearish']),
                "system_version": "16+2-agents"
            }
            
            logger.info(f"Pushing {len(picks)} picks to Firebase...")
            
            # Push to Firebase Realtime Database
            url = f"{self.database_url}/picks/latest.json"
            
            async with self.session.put(url, json=firebase_data) as response:
                if response.status == 200:
                    logger.info(f"Successfully pushed {len(picks)} picks to Firebase")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to push picks to Firebase: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pushing picks to Firebase: {e}")
            return False
    
    async def push_watchlist_update(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Push watchlist stock update to Firebase
        
        Args:
            symbol: Stock symbol
            data: Updated stock data
            
        Returns:
            bool: Success status
        """
        try:
            url = f"{self.database_url}/watchlist/{symbol}.json"
            
            firebase_data = {
                "symbol": symbol,
                "current_price": data.get("current_price", 0.0),
                "change_percent": data.get("change_percent", 0.0),
                "sentiment_score": data.get("sentiment_score", 0.0),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "news_sentiment": data.get("news_sentiment", {}),
                "social_sentiment": data.get("social_sentiment", {})
            }
            
            async with self.session.put(url, json=firebase_data) as response:
                if response.status == 200:
                    logger.info(f"Successfully updated watchlist for {symbol}")
                    return True
                else:
                    logger.error(f"Failed to update watchlist for {symbol}: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating watchlist for {symbol}: {e}")
            return False
    
    async def push_analytics_update(self, analytics_data: Dict[str, Any]) -> bool:
        """
        Push analytics data to Firebase
        
        Args:
            analytics_data: Analytics data dictionary
            
        Returns:
            bool: Success status
        """
        try:
            url = f"{self.database_url}/analytics/latest.json"
            
            firebase_data = {
                "accuracy_metrics": analytics_data.get("accuracy_metrics", {}),
                "performance_history": analytics_data.get("performance_history", []),
                "win_rate": analytics_data.get("win_rate", 0.0),
                "total_picks": analytics_data.get("total_picks", 0),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            async with self.session.put(url, json=firebase_data) as response:
                if response.status == 200:
                    logger.info("Successfully updated analytics data")
                    return True
                else:
                    logger.error(f"Failed to update analytics: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
            return False
    
    async def get_latest_picks(self) -> Optional[Dict[str, Any]]:
        """Get latest picks from Firebase"""
        try:
            await self._ensure_session()
            
            url = f"{self.database_url}/picks/latest.json"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Failed to get picks from Firebase: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting picks from Firebase: {e}")
            return None
    
    async def initialize_firebase_structure(self) -> bool:
        """
        Initialize Firebase database structure
        
        Returns:
            bool: Success status
        """
        try:
            # Initialize basic structure
            initial_structure = {
                "picks": {
                    "latest": {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "picks": [],
                        "metadata": {
                            "total_picks": 0,
                            "system_version": "18-agent-v1.0",
                            "status": "initialized"
                        }
                    }
                },
                "watchlist": {},
                "analytics": {
                    "latest": {
                        "accuracy_metrics": {},
                        "performance_history": [],
                        "win_rate": 0.0,
                        "total_picks": 0,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
            
            # Push initial structure
            url = f"{self.database_url}/.json"
            
            async with self.session.patch(url, json=initial_structure) as response:
                if response.status == 200:
                    logger.info("Successfully initialized Firebase structure")
                    return True
                else:
                    logger.error(f"Failed to initialize Firebase: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            return False

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None

# Convenience functions for easy integration
async def push_picks_to_firebase(picks: List[Dict[str, Any]]) -> bool:
    """Convenience function to push picks to Firebase"""
    async with FirebaseService() as firebase:
        return await firebase.push_picks_to_firebase(picks)

async def initialize_firebase() -> bool:
    """Convenience function to initialize Firebase structure"""
    async with FirebaseService() as firebase:
        return await firebase.initialize_firebase_structure()

# Test function
async def test_firebase_connection():
    """Test Firebase connection and basic operations"""
    print("🔥 Testing Firebase Connection...")
    
    async with FirebaseService() as firebase:
        # Test initialization
        init_success = await firebase.initialize_firebase_structure()
        print(f"✅ Firebase initialization: {'SUCCESS' if init_success else 'FAILED'}")
        
        # Test pushing sample picks
        sample_picks = [
            {
                "symbol": "TSLA",
                "direction": "bullish",
                "confidence": 0.75,
                "target_low": 250.0,
                "target_medium": 275.0,
                "target_high": 300.0,
                "current_price": 240.0,
                "reasoning": "Strong technical breakout with high volume",
                "risk_level": "medium",
                "estimated_days": 7
            }
        ]
        
        push_success = await firebase.push_picks_to_firebase(sample_picks)
        print(f"✅ Sample picks push: {'SUCCESS' if push_success else 'FAILED'}")
        
        # Test getting picks back
        retrieved_picks = await firebase.get_latest_picks()
        print(f"✅ Retrieve picks: {'SUCCESS' if retrieved_picks else 'FAILED'}")
        
        if retrieved_picks:
            print(f"   Retrieved {len(retrieved_picks.get('picks', []))} picks")
    
    print("🎉 Firebase testing complete!")

if __name__ == "__main__":
    asyncio.run(test_firebase_connection())
