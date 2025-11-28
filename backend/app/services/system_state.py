# app/services/system_state.py
import os
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

redis_client = Redis.from_url(os.getenv("REDIS_URL"))


async def is_system_on() -> bool:
    try:
        value = await redis_client.get("system:state")
        return value == b"ON"
    except ConnectionError:
        # Fallback: if Redis down, assume ON (safe default)
        return True


async def set_system_on(state: bool):
    value = b"ON" if state else b"OFF"
    await redis_client.set("system:state", value, ex=60*60*24*30)  # 30-day TTL