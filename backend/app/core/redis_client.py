"""
Redis client configuration and utilities.
"""
import json
import logging
from typing import Any, Optional, Union
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
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.client.ping()
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


# Global Redis client instance
redis_client = RedisClient()
