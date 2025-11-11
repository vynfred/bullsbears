#!/usr/bin/env python3
"""
Database Migration Script for BullsBears v3.3
Migrates from legacy pick_candidates to new shortlist_candidates + final_picks schema
"""

import logging
from datetime import datetime
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                )
            """), {"table_name": table_name})
            return result.fetchone()[0]
    except Exception as e:
        logger.error(f"Error checking table {table_name}: {e}")
        return False


def backup_legacy_tables():
    """Create backup of legacy tables before migration"""
    logger.info("Creating backup of legacy tables...")

    with engine.connect() as conn:
        # Check if legacy tables exist and create backups
        legacy_tables = [
            'pick_candidates',
            'candidate_price_tracking',
            'candidate_retrospective_analysis',
            'candidate_model_learning'
        ]

        for table in legacy_tables:
            if check_table_exists(table):
                backup_name = f"{table}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    conn.execute(text(f"CREATE TABLE {backup_name} AS SELECT * FROM {table}"))
                    conn.commit()
                    logger.info(f"✅ Backed up {table} to {backup_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not backup {table}: {e}")


def create_new_tables():
    """Create new tables using SQLAlchemy models"""
    logger.info("Creating new table schema...")

    try:
        # Import models to register them
        from app.models.pick_candidates import ShortListCandidate, FinalPick
        from app.core.database import Base

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ New tables created successfully")

    except Exception as e:
        logger.error(f"❌ Failed to create new tables: {e}")
        raise


async def migrate_data():
    """Migrate data from legacy tables to new schema"""
    logger.info("Migrating data from legacy tables...")
    
    db_pool = await get_asyncpg_pool()
    async with db_pool.acquire() as conn:

        # Check if legacy pick_candidates table exists
        if not await check_table_exists('pick_candidates'):
            logger.info("No legacy pick_candidates table found - skipping data migration")
            return
            
        try:
            # Migrate pick_candidates to shortlist_candidates
            await conn.execute("""
                INSERT INTO shortlist_candidates (
                    symbol, date, rank, prescreen_reason,
                    wyckoff_phase_2, weekly_triangle_coil, volume_shelf_breakout,
                    p_shape_profile, fakeout_wick_rejection, spring_setup,
                    social_score, headlines, events, polymarket_prob,
                    selected, arbitrator_model, arbitrator_reason,
                    target_low, target_high, stop_loss, support_level,
                    max_gain_pct, final_gain_pct, moon_20pct, rug_20pct,
                    created_at
                )
                SELECT 
                    ticker as symbol,
                    prediction_date as date,
                    COALESCE(rank, 1) as rank,
                    reasoning as prescreen_reason,
                    false as wyckoff_phase_2,
                    false as weekly_triangle_coil, 
                    false as volume_shelf_breakout,
                    false as p_shape_profile,
                    false as fakeout_wick_rejection,
                    false as spring_setup,
                    0 as social_score,
                    null as headlines,
                    null as events,
                    null as polymarket_prob,
                    COALESCE(selected_by_arbitrator, false) as selected,
                    arbitrator_model,
                    arbitrator_reasoning as arbitrator_reason,
                    target_price_low as target_low,
                    target_price_high as target_high,
                    stop_loss_price as stop_loss,
                    support_level_price as support_level,
                    max_gain_percent as max_gain_pct,
                    final_outcome_percent as final_gain_pct,
                    (max_gain_percent >= 20.0) as moon_20pct,
                    (final_outcome_percent <= -20.0) as rug_20pct,
                    created_at
                FROM pick_candidates
                WHERE ticker IS NOT NULL
            """)
            
            migrated_count = await conn.fetchval("SELECT COUNT(*) FROM shortlist_candidates")
            logger.info(f"✅ Migrated {migrated_count} records to shortlist_candidates")
            
            # Migrate selected picks to final_picks
            await conn.execute("""
                INSERT INTO final_picks (
                    date, symbol, direction, confidence,
                    target_low, target_high, stop_loss, support_level,
                    reason, arbitrator_model, shortlist_id
                )
                SELECT 
                    sc.date,
                    sc.symbol,
                    CASE WHEN sc.target_high > 0 THEN 'moon' ELSE 'rug' END as direction,
                    75 as confidence,  -- Default confidence
                    sc.target_low,
                    sc.target_high,
                    sc.stop_loss,
                    sc.support_level,
                    sc.arbitrator_reason as reason,
                    sc.arbitrator_model,
                    sc.id as shortlist_id
                FROM shortlist_candidates sc
                WHERE sc.selected = true
            """)
            
            final_picks_count = await conn.fetchval("SELECT COUNT(*) FROM final_picks")
            logger.info(f"✅ Migrated {final_picks_count} records to final_picks")
            
        except Exception as e:
            logger.error(f"❌ Data migration failed: {e}")
            raise


async def cleanup_legacy_tables():
    """Drop legacy tables after successful migration"""
    logger.info("Cleaning up legacy tables...")
    
    db_pool = await get_asyncpg_pool()
    async with db_pool.acquire() as conn:

        legacy_tables = [
            'candidate_model_learning',
            'candidate_retrospective_analysis', 
            'candidate_price_tracking',
            'pick_candidates'
        ]
        
        for table in legacy_tables:
            if await check_table_exists(table):
                try:
                    await conn.execute(f"DROP TABLE {table}")
                    logger.info(f"✅ Dropped legacy table: {table}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not drop {table}: {e}")


async def verify_migration():
    """Verify the migration was successful"""
    logger.info("Verifying migration...")
    
    db_pool = await get_asyncpg_pool()
    async with db_pool.acquire() as conn:

        # Check new tables exist and have data
        shortlist_count = await conn.fetchval("SELECT COUNT(*) FROM shortlist_candidates")
        final_picks_count = await conn.fetchval("SELECT COUNT(*) FROM final_picks")
        
        logger.info(f"✅ Migration verification:")
        logger.info(f"   - shortlist_candidates: {shortlist_count} records")
        logger.info(f"   - final_picks: {final_picks_count} records")
        
        if shortlist_count == 0:
            logger.warning("⚠️ No data in shortlist_candidates - this may be expected for a fresh install")


def main():
    """Run the complete migration process"""
    logger.info("🚀 Starting BullsBears database migration...")

    try:
        # Test database connection
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            logger.info(f"✅ Database connection successful: {result.fetchone()}")

        # Step 1: Backup legacy tables
        backup_legacy_tables()

        # Step 2: Create new tables
        create_new_tables()

        logger.info("✅ Basic migration completed successfully!")
        logger.info("💡 Tables created. Data migration can be done separately if needed.")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
