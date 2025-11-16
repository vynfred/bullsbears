"""
Watchlist API endpoints with Firebase Auth integration
Requires user authentication for all operations
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncpg
import aiohttp
import os
import logging

from ...core.database import get_asyncpg_pool

router = APIRouter()
logger = logging.getLogger(__name__)

# FMP API configuration
FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class WatchlistEntry(BaseModel):
    """Watchlist entry model"""
    id: Optional[int] = None
    symbol: str
    name: Optional[str] = None
    entry_type: str  # 'bullish' or 'bearish'
    entry_price: float
    target_price: float
    ai_confidence_score: float
    ai_recommendation: str
    added_at: Optional[datetime] = None
    user_id: Optional[str] = None


class AddWatchlistRequest(BaseModel):
    """Request model for adding to watchlist"""
    symbol: str
    name: Optional[str] = None
    entry_type: str
    entry_price: float
    target_price: float
    ai_confidence_score: float
    ai_recommendation: str


class WatchlistNotification(BaseModel):
    """Watchlist notification model"""
    id: str
    symbol: str
    type: str  # 'target_hit', 'sentiment_change', 'price_alert'
    message: str
    timestamp: datetime
    data: Optional[Dict] = None


async def get_user_id_from_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from Firebase Auth token
    In production, this should verify the token with Firebase Admin SDK
    For now, we'll extract it from the Authorization header
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Expected format: "Bearer <firebase_token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    # TODO: Verify token with Firebase Admin SDK
    # For now, we'll use a placeholder
    # In production, use:
    # from firebase_admin import auth
    # decoded_token = auth.verify_id_token(token)
    # user_id = decoded_token['uid']
    
    # Temporary: extract user_id from token (REPLACE IN PRODUCTION)
    try:
        # This is a placeholder - in production, verify with Firebase
        user_id = token  # Replace with actual token verification
        return user_id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def fetch_real_time_quotes(symbols: List[str]) -> Dict[str, Dict]:
    """
    Fetch real-time quotes from FMP API for multiple symbols
    Returns dict mapping symbol -> {price, change, change_percent}
    """
    if not FMP_API_KEY or not symbols:
        return {}

    try:
        # FMP allows batch quotes with comma-separated symbols
        symbols_str = ",".join(symbols[:50])  # Limit to 50 symbols per request
        url = f"{FMP_BASE_URL}/quote-short/{symbols_str}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"apikey": FMP_API_KEY}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # Convert list to dict keyed by symbol
                    quotes = {}
                    for quote in data:
                        if quote.get("symbol") and quote.get("price"):
                            quotes[quote["symbol"]] = {
                                "price": float(quote["price"]),
                                "volume": int(quote.get("volume", 0))
                            }

                    return quotes
                else:
                    logger.error(f"FMP API error: {resp.status}")
                    return {}

    except Exception as e:
        logger.error(f"Failed to fetch real-time quotes: {e}")
        return {}


@router.get("/", response_model=List[WatchlistEntry])
async def get_watchlist(user_id: str = Depends(get_user_id_from_token)):
    """
    Get all watchlist entries for authenticated user with real-time prices
    Includes current_price, price_change, price_change_percent, and days_held
    """
    try:
        db = await get_asyncpg_pool()

        # Fetch watchlist entries
        rows = await db.fetch("""
            SELECT id, symbol, name, entry_type, entry_price, target_price,
                   ai_confidence_score, ai_recommendation, added_at, user_id
            FROM watchlist
            WHERE user_id = $1
            ORDER BY added_at DESC
        """, user_id)

        if not rows:
            return []

        # Extract symbols for batch quote fetch
        symbols = [row["symbol"] for row in rows]

        # Fetch real-time quotes
        quotes = await fetch_real_time_quotes(symbols)

        # Enrich entries with real-time data
        entries = []
        for row in rows:
            entry = dict(row)
            symbol = row["symbol"]
            entry_price = float(row["entry_price"])

            # Add real-time price data
            if symbol in quotes:
                current_price = quotes[symbol]["price"]
                entry["current_price"] = current_price
                entry["price_change"] = current_price - entry_price
                entry["price_change_percent"] = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0
            else:
                # Fallback to entry price if quote unavailable
                entry["current_price"] = entry_price
                entry["price_change"] = 0.0
                entry["price_change_percent"] = 0.0

            # Calculate days held
            if row["added_at"]:
                days_held = (datetime.now() - row["added_at"]).days
                entry["days_held"] = days_held
            else:
                entry["days_held"] = 0

            entries.append(entry)

        return entries

    except Exception as e:
        logger.error(f"Failed to fetch watchlist: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=WatchlistEntry)
async def add_to_watchlist(
    request: AddWatchlistRequest,
    user_id: str = Depends(get_user_id_from_token)
):
    """Add stock to watchlist for authenticated user"""

    try:
        db = await get_asyncpg_pool()

        # Check if already in watchlist
        existing = await db.fetchval("""
            SELECT id FROM watchlist
            WHERE user_id = $1 AND symbol = $2
        """, user_id, request.symbol)

        if existing:
            raise HTTPException(status_code=400, detail=f"{request.symbol} already in watchlist")

        # Insert new entry
        row = await db.fetchrow("""
            INSERT INTO watchlist (
                user_id, symbol, name, entry_type, entry_price, target_price,
                ai_confidence_score, ai_recommendation, added_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING id, symbol, name, entry_type, entry_price, target_price,
                      ai_confidence_score, ai_recommendation, added_at, user_id
        """, user_id, request.symbol, request.name, request.entry_type,
            request.entry_price, request.target_price, request.ai_confidence_score,
            request.ai_recommendation)

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add to watchlist: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    user_id: str = Depends(get_user_id_from_token)
):
    """Remove stock from watchlist for authenticated user"""

    try:
        db = await get_asyncpg_pool()

        # Delete entry
        result = await db.execute("""
            DELETE FROM watchlist
            WHERE user_id = $1 AND symbol = $2
        """, user_id, symbol)

        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")

        return {"success": True, "message": f"{symbol} removed from watchlist"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from watchlist: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/notifications", response_model=List[WatchlistNotification])
async def get_watchlist_notifications(user_id: str = Depends(get_user_id_from_token)):
    """
    Get notifications for watchlist stocks
    Returns alerts for target hits, sentiment changes, and price movements
    """
    try:
        db = await get_asyncpg_pool()

        # Get user's watchlist
        watchlist_rows = await db.fetch("""
            SELECT symbol, entry_type, entry_price, target_price, added_at
            FROM watchlist
            WHERE user_id = $1
        """, user_id)

        if not watchlist_rows:
            return []

        # Fetch real-time quotes
        symbols = [row["symbol"] for row in watchlist_rows]
        quotes = await fetch_real_time_quotes(symbols)

        notifications = []

        for row in watchlist_rows:
            symbol = row["symbol"]
            entry_type = row["entry_type"]
            entry_price = float(row["entry_price"])
            target_price = float(row["target_price"])

            if symbol not in quotes:
                continue

            current_price = quotes[symbol]["price"]
            price_change_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0

            # Target hit notification
            if entry_type == "bullish" and current_price >= target_price:
                notifications.append(WatchlistNotification(
                    id=f"{symbol}_target_hit",
                    symbol=symbol,
                    type="target_hit",
                    message=f"{symbol} hit your bullish target of ${target_price:.2f}! Current: ${current_price:.2f}",
                    timestamp=datetime.now(),
                    data={"current_price": current_price, "target_price": target_price, "gain_percent": price_change_percent}
                ))
            elif entry_type == "bearish" and current_price <= target_price:
                notifications.append(WatchlistNotification(
                    id=f"{symbol}_target_hit",
                    symbol=symbol,
                    type="target_hit",
                    message=f"{symbol} hit your bearish target of ${target_price:.2f}! Current: ${current_price:.2f}",
                    timestamp=datetime.now(),
                    data={"current_price": current_price, "target_price": target_price, "gain_percent": abs(price_change_percent)}
                ))

            # Significant price movement alerts (>5% change)
            if abs(price_change_percent) >= 5.0:
                direction = "up" if price_change_percent > 0 else "down"
                notifications.append(WatchlistNotification(
                    id=f"{symbol}_price_alert",
                    symbol=symbol,
                    type="price_alert",
                    message=f"{symbol} moved {direction} {abs(price_change_percent):.1f}% since you added it",
                    timestamp=datetime.now(),
                    data={"current_price": current_price, "entry_price": entry_price, "change_percent": price_change_percent}
                ))

        return notifications

    except Exception as e:
        logger.error(f"Failed to fetch watchlist notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")
