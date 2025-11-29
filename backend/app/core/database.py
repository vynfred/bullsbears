# backend/app/core/database.py
"""
Database – BullsBears v5 (Render Edition)
Uses only DATABASE_URL from Render environment
No host/user/pass parsing, no Unix sockets, no retry loops
"""

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncpg
from asyncpg import Pool

logger = logging.getLogger(__name__)

# Get DATABASE_URL from Render (internal URL)
DATABASE_URL = os.environ["DATABASE_URL"]

# Auto-fix Render's postgres:// or postgresql:// → postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine — Render Postgres is always available
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=False,  # set to True only if debugging
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncSession:
    """
    Dependency for FastAPI routes and Celery tasks
    Yields an async SQLAlchemy session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Optional: close engine on shutdown (Render handles this, but safe to have)
async def close_db():
    """Close database connections"""
    await engine.dispose()
    await close_asyncpg_pool()

_asyncpg_pool: Pool = None

async def get_asyncpg_pool() -> Pool:
    """Get asyncpg connection pool for raw SQL queries"""
    global _asyncpg_pool

    if _asyncpg_pool is None:
        # Extract connection details from DATABASE_URL
        import urllib.parse
        import ssl

        parsed = urllib.parse.urlparse(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

        # Create SSL context for Render PostgreSQL
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        _asyncpg_pool = await asyncpg.create_pool(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
            min_size=1,
            max_size=10,
            ssl=ssl_context,  # Enable SSL for Render
            command_timeout=60,  # 60 second timeout per command
        )
        logger.info(f"asyncpg pool created: {parsed.hostname}")

    return _asyncpg_pool

async def close_asyncpg_pool():
    """Close asyncpg pool"""
    global _asyncpg_pool
    if _asyncpg_pool:
        await _asyncpg_pool.close()
        _asyncpg_pool = None
