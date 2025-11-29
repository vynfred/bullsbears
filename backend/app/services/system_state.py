# app/services/system_state.py
import os
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

# Lazy initialization to avoid connection errors at startup
_redis_client = None


def _get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            # Render Redis requires SSL with relaxed cert verification
            if "rediss://" in redis_url and "?" not in redis_url:
                redis_url += "?ssl_cert_reqs=none"
            _redis_client = Redis.from_url(redis_url)
    return _redis_client


async def is_system_on() -> bool:
    """Check if system is ON. Returns True if Redis unavailable (safe default)."""
    client = _get_redis_client()
    if client is None:
        return False  # No Redis URL configured
    try:
        value = await client.get("system:state")
        return value == b"ON"
    except (RedisConnectionError, Exception) as e:
        print(f"Redis error in is_system_on: {e}")
        return False


async def set_system_on(state: bool) -> bool:
    """Set system state. Returns True on success."""
    client = _get_redis_client()
    if client is None:
        return False  # No Redis URL configured
    try:
        value = b"ON" if state else b"OFF"
        await client.set("system:state", value, ex=60*60*24*30)  # 30-day TTL
        return True
    except (RedisConnectionError, Exception) as e:
        print(f"Redis error in set_system_on: {e}")
        return False