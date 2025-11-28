# backend/app/services/push_picks_to_firebase.py
import logging
from datetime import datetime
from app.core.firebase import db

logger = logging.getLogger(__name__)

def publish_picks_to_firebase(picks_data: dict):
    """Sync publish — used by run_arbitrator task"""
    try:
        db.child("pulse/latest").set({
            "timestamp": datetime.now().isoformat(),
            "bullish_picks": picks_data.get("bullish", []),
            "bearish_picks": picks_data.get("bearish", []),
            "total_picks": picks_data.get("total_picks", 0),
            "scan_completed": True,
            "next_scan": "tomorrow_0830_et"
        })
        logger.info("Picks published to Firebase pulse/latest")
    except Exception as e:
        logger.error(f"Firebase publish failed: {e}")