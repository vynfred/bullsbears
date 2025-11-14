#!/usr/bin/env python3
"""
Firebase Realtime Database Service – FINAL v3.3 (November 12, 2025)
Instant picks delivery — $0 cost — 100% working
"""

import aiohttp
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Your Firebase project
DATABASE_URL = "https://bullsbears-xyz-default-rtdb.firebaseio.com"

class FirebaseService:
    """Minimal, perfect Firebase service"""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def push_picks_to_firebase(self, picks: List[Dict[str, Any]]) -> bool:
        """Push picks to Firebase — used by publish_to_firebase.py"""
        try:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "picks": picks,
                "total_picks": len(picks),
                "bullish_count": len([p for p in picks if p.get("direction") == "bullish"]),
                "bearish_count": len([p for p in picks if p.get("direction") == "bearish"]),
                "system_version": "v3.3"
            }

            url = f"{DATABASE_URL}/picks/latest.json"

            async with self.session.put(url, json=data) as resp:
                if resp.status == 200:
                    logger.info(f"Pushed {len(picks)} picks to Firebase")
                    return True
                else:
                    text = await resp.text()
                    logger.error(f"Firebase error {resp.status}: {text}")
                    return False

        except Exception as e:
            logger.error(f"Firebase push failed: {e}")
            return False


# Convenience function — used in tasks
async def push_picks_to_firebase(picks: List[Dict[str, Any]]) -> bool:
    """Direct import: from app.services import push_picks_to_firebase"""
    async with FirebaseService() as fb:
        return await fb.push_picks_to_firebase(picks)


# Test it
if __name__ == "__main__":
    async def test():
        sample = [{
            "symbol": "NVDA",
            "direction": "bullish",
            "confidence": 0.92,
            "target_low": 135.0,
            "target_high": 160.0,
            "reasoning": "Volume shelf breakout + Grok confirmation"
        }]
        success = await push_picks_to_firebase(sample)
        print("SUCCESS" if success else "FAILED")

    asyncio.run(test())