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

logger = logging.getLogger(__name__)

# Get DATABASE_URL from Render (internal URL)
DATABASE_URL = os.environ["DATABASE_URL"]

# Auto-fix Render's postgres:// → postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

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
    await engine.dispose()
    logger.info("Database engine disposed")