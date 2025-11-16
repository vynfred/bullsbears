"""
Database configuration – FINAL v3.3 (November 11, 2025)
Sync + Async PostgreSQL only. No SQLite. No leaks. No surprises.
"""

import logging
from typing import AsyncGenerator
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
import os

from .config import settings

logger = logging.getLogger(__name__)

# Create base class for models
Base = declarative_base()

# === SYNC ENGINE (for migrations, admin tools) ===
database_url = settings.get_database_url()
sync_engine = create_engine(
    database_url.replace("postgresql+asyncpg://", "postgresql://") if "postgresql+asyncpg://" in database_url else database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug,
    pool_size=3,
    max_overflow=5,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)

# Backward compatibility alias
engine = sync_engine

def get_sync_db() -> Session:
    db = SyncSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Sync DB error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# === ASYNC ENGINE (for all agents + API) ===
async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://") if "postgresql://" in database_url else database_url
async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug,
    future=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Primary dependency – used by FastAPI + all agents"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Async DB error: {e}")
            await session.rollback()
            raise

# === LEGACY asyncpg pool (kept for raw queries) ===
_async_pool = None

async def get_asyncpg_pool() -> asyncpg.Pool:
    """
    Get or create asyncpg connection pool with retry logic for Cloud Run startup.
    Supports both Cloud SQL Unix socket and TCP connections.
    """
    global _async_pool
    if _async_pool is not None:
        return _async_pool

    import asyncio

    max_retries = 10
    base_delay = 2  # seconds

    # Check if using Cloud SQL Unix socket
    is_unix_socket = settings.database_host.startswith("/cloudsql/")

    if is_unix_socket:
        logger.info(f"🔌 Connecting to Cloud SQL via Unix socket: {settings.database_host}")
        connection_params = {
            "host": settings.database_host,
            "database": settings.database_name,
            "user": settings.database_user,
            "password": settings.database_password,
            "min_size": 1,
            "max_size": 10,
            "command_timeout": 60,
            "timeout": 30,
        }
    else:
        database_url = settings.get_database_url()
        logger.info(f"🔌 Connecting to PostgreSQL via TCP: {database_url.split('@')[0] if '@' in database_url else 'localhost'}@...")
        connection_params = {
            "dsn": database_url.replace("+asyncpg", ""),
            "min_size": 1,
            "max_size": 10,
            "command_timeout": 60,
            "timeout": 30,
        }

    # Retry loop with exponential backoff
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"📡 Database connection attempt {attempt}/{max_retries}...")
            _async_pool = await asyncpg.create_pool(**connection_params)
            logger.info(f"✅ Database pool created successfully after {attempt} attempt(s)")
            return _async_pool
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Connection attempt {attempt}/{max_retries} failed: {error_msg[:100]}")

            if attempt == max_retries:
                logger.error(f"❌ Failed to connect to database after {max_retries} attempts")
                logger.error(f"Connection params: host={settings.database_host}, db={settings.database_name}, user={settings.database_user}")
                raise

            # Exponential backoff: 2s, 4s, 6s, 8s, 10s, 12s...
            delay = min(base_delay * attempt, 15)
            logger.info(f"⏳ Retrying in {delay} seconds...")
            await asyncio.sleep(delay)

    return _async_pool

async def close_asyncpg_pool():
    global _async_pool
    if _async_pool:
        await _async_pool.close()
        _async_pool = None
        logger.info("asyncpg pool closed")

# === DB INIT & CLOSE ===
async def init_db():
    """
    Initialize database connection.
    Note: Tables are already created via migrations, so we just verify connection.
    """
    try:
        # Test connection by getting a pool
        await get_asyncpg_pool()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

async def close_db():
    await async_engine.dispose()
    await close_asyncpg_pool()
    logger.info("Database connections closed")