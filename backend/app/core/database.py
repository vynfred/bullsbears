"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import asyncpg
import logging
from typing import Optional

from .config import settings

logger = logging.getLogger(__name__)

# Create database engine
if "sqlite" in settings.database_url:
    # SQLite configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug,
        pool_size=20,
        max_overflow=30,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def init_db():
    """Initialize database tables."""
    try:
        # Import all models to ensure they're registered
        from ..models import stock, options_data, user_preferences, analysis_results, watchlist, pick_candidates

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Close database connections."""
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


# Async database connection for agent system
_async_db_pool: Optional[asyncpg.Pool] = None


async def get_database() -> asyncpg.Pool:
    """Get async database connection pool for agent system"""
    global _async_db_pool

    if _async_db_pool is None:
        try:
            # Extract connection details from DATABASE_URL
            if settings.database_url.startswith('postgresql://'):
                _async_db_pool = await asyncpg.create_pool(
                    settings.database_url,
                    min_size=5,
                    max_size=20,
                    command_timeout=30
                )
                logger.info("Async database pool created successfully")
            else:
                logger.error("Async database only supports PostgreSQL")
                raise ValueError("Async database requires PostgreSQL")

        except Exception as e:
            logger.error(f"Failed to create async database pool: {e}")
            raise

    return _async_db_pool


async def close_async_db():
    """Close async database pool"""
    global _async_db_pool

    if _async_db_pool:
        await _async_db_pool.close()
        _async_db_pool = None
        logger.info("Async database pool closed")
