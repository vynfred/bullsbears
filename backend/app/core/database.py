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
    pool_size=10,
    max_overflow=20,
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
    global _async_pool
    if _async_pool is None:
        database_url = settings.get_database_url()
        _async_pool = await asyncpg.create_pool(
            dsn=database_url.replace("+asyncpg", ""),
            min_size=5,
            max_size=30,
            command_timeout=30,
        )
        logger.info("asyncpg pool created")
    return _async_pool

async def close_asyncpg_pool():
    global _async_pool
    if _async_pool:
        await _async_pool.close()
        _async_pool = None
        logger.info("asyncpg pool closed")

# === DB INIT & CLOSE ===
async def init_db():
    from ..models import Base  # Import here to avoid circular imports
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created")

async def close_db():
    await async_engine.dispose()
    await close_asyncpg_pool()
    logger.info("Database connections closed")