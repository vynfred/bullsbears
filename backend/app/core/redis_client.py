# backend/app/core/redis_client.py
"""
Redis Client - Async Redis connection for BullsBears
"""

import redis.asyncio as redis
from typing import Optional
from .config import settings

_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create async Redis client"""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    return _redis_client


async def close_redis_client():
    """Close Redis connection"""
    global _redis_client
    
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

