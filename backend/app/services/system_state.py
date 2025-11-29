# app/services/system_state.py
import os
import asyncio
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

# Lazy initialization to avoid connection errors at startup
_redis_client = None

# Timeout for Redis operations (seconds)
REDIS_TIMEOUT = 3


def _get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            # Render Redis requires SSL with relaxed cert verification
            if "rediss://" in redis_url and "?" not in redis_url:
                redis_url += "?ssl_cert_reqs=none"
            _redis_client = Redis.from_url(redis_url, socket_timeout=REDIS_TIMEOUT, socket_connect_timeout=REDIS_TIMEOUT)
    return _redis_client


async def is_system_on() -> bool:
    """Check if system is ON. Returns False if Redis unavailable."""
    client = _get_redis_client()
    if client is None:
        return False  # No Redis URL configured
    try:
        value = await asyncio.wait_for(client.get("system:state"), timeout=REDIS_TIMEOUT)
        return value == b"ON"
    except asyncio.TimeoutError:
        print("Redis timeout in is_system_on")
        return False
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
        await asyncio.wait_for(
            client.set("system:state", value, ex=60*60*24*30),  # 30-day TTL
            timeout=REDIS_TIMEOUT
        )
        return True
    except asyncio.TimeoutError:
        print("Redis timeout in set_system_on")
        return False
    except (RedisConnectionError, Exception) as e:
        print(f"Redis error in set_system_on: {e}")
        return False