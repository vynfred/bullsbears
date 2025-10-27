"""
Redis client configuration and utilities.
"""
import asyncio
import json
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from .config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with caching utilities."""
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection pool."""
        try:
            self.pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True,
                socket_connect_timeout=5,  # 5 second timeout
                socket_timeout=5
            )
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection with timeout
            await asyncio.wait_for(self.client.ping(), timeout=5.0)
            logger.info("Redis connection established successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connections."""
        try:
            if self.client:
                await self.client.close()
            if self.pool:
                await self.pool.disconnect()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with JSON deserialization."""
        try:
            if not self.client:
                await self.connect()
            
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis with JSON serialization."""
        try:
            if not self.client:
                await self.connect()
            
            # Serialize value to JSON if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            result = await self.client.set(key, value, ex=expire)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            if not self.client:
                await self.connect()
            
            result = await self.client.delete(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            if not self.client:
                await self.connect()
            
            result = await self.client.exists(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def cache_with_ttl(
        self, 
        key: str, 
        value: Any, 
        ttl: int
    ) -> bool:
        """Cache value with time-to-live."""
        return await self.set(key, value, expire=ttl)
    
    async def get_or_set(
        self, 
        key: str, 
        default_value: Any, 
        ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache or set default if not exists."""
        value = await self.get(key)
        if value is None:
            await self.set(key, default_value, expire=ttl)
            return default_value
        return value

    # Enhanced methods for precomputed analysis system

    async def get_with_ttl(self, key: str) -> tuple[Any, Optional[int]]:
        """Get value from Redis along with its TTL."""
        try:
            if not self.client:
                await self.connect()

            # Get value and TTL in pipeline for efficiency
            pipe = self.client.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            results = await pipe.execute()

            value, ttl = results
            if value is None:
                return None, None

            # Try to deserialize JSON, fallback to string
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass

            return value, ttl if ttl > 0 else None

        except Exception as e:
            logger.error(f"Redis GET_WITH_TTL error for key {key}: {e}")
            return None, None

    async def set_with_metadata(
        self,
        key: str,
        value: Any,
        ttl: int,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Set value with metadata for tracking freshness and source."""
        try:
            if not self.client:
                await self.connect()

            # Add metadata to the value
            data_with_metadata = {
                "data": value,
                "metadata": {
                    "cached_at": datetime.now().isoformat(),
                    "ttl": ttl,
                    "source": "precomputed",
                    **(metadata or {})
                }
            }

            serialized_value = json.dumps(data_with_metadata, default=str)
            result = await self.client.set(key, serialized_value, ex=ttl)
            return bool(result)

        except Exception as e:
            logger.error(f"Redis SET_WITH_METADATA error for key {key}: {e}")
            return False

    async def get_with_metadata(self, key: str) -> tuple[Any, Optional[Dict]]:
        """Get value along with its metadata."""
        try:
            if not self.client:
                await self.connect()

            value = await self.client.get(key)
            if value is None:
                return None, None

            try:
                data_with_metadata = json.loads(value)
                if isinstance(data_with_metadata, dict) and "data" in data_with_metadata:
                    return data_with_metadata["data"], data_with_metadata.get("metadata")
                else:
                    # Fallback for data without metadata
                    return data_with_metadata, None
            except (json.JSONDecodeError, TypeError):
                return value, None

        except Exception as e:
            logger.error(f"Redis GET_WITH_METADATA error for key {key}: {e}")
            return None, None

    async def track_cache_hit(self, key_pattern: str, hit: bool = True):
        """Track cache hit/miss rates for monitoring."""
        try:
            if not self.client:
                await self.connect()

            # Use daily counters for hit rate tracking
            today = datetime.now().strftime("%Y-%m-%d")
            hit_key = f"cache_hits:{key_pattern}:{today}"
            miss_key = f"cache_misses:{key_pattern}:{today}"

            if hit:
                await self.client.incr(hit_key)
                await self.client.expire(hit_key, 86400 * 2)  # Keep for 2 days
            else:
                await self.client.incr(miss_key)
                await self.client.expire(miss_key, 86400 * 2)  # Keep for 2 days

        except Exception as e:
            logger.error(f"Error tracking cache hit for {key_pattern}: {e}")

    async def get_cache_stats(self, key_pattern: str) -> Dict[str, int]:
        """Get cache hit rate statistics."""
        try:
            if not self.client:
                await self.connect()

            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # Get stats for today and yesterday
            pipe = self.client.pipeline()
            pipe.get(f"cache_hits:{key_pattern}:{today}")
            pipe.get(f"cache_misses:{key_pattern}:{today}")
            pipe.get(f"cache_hits:{key_pattern}:{yesterday}")
            pipe.get(f"cache_misses:{key_pattern}:{yesterday}")
            results = await pipe.execute()

            hits_today = int(results[0] or 0)
            misses_today = int(results[1] or 0)
            hits_yesterday = int(results[2] or 0)
            misses_yesterday = int(results[3] or 0)

            total_today = hits_today + misses_today
            total_yesterday = hits_yesterday + misses_yesterday

            return {
                "hits_today": hits_today,
                "misses_today": misses_today,
                "total_today": total_today,
                "hit_rate_today": (hits_today / total_today * 100) if total_today > 0 else 0,
                "hits_yesterday": hits_yesterday,
                "misses_yesterday": misses_yesterday,
                "total_yesterday": total_yesterday,
                "hit_rate_yesterday": (hits_yesterday / total_yesterday * 100) if total_yesterday > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting cache stats for {key_pattern}: {e}")
            return {}

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        try:
            if not self.client:
                await self.connect()

            # Find all keys matching the pattern
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"Invalidated {deleted} keys matching pattern: {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error invalidating pattern {pattern}: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()

async def get_redis_client() -> RedisClient:
    """Get the global Redis client instance."""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client
