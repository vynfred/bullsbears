#!/usr/bin/env python3
"""
Migration script to add precompute analysis tables.
Run this script to update the database schema for the precompute system.
"""
import sys
import os
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.database import engine, Base
from app.models.precomputed_analysis import PrecomputedAnalysis, PrecomputeJobStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the database migration to add precompute tables."""
    try:
        logger.info("Starting database migration for precompute system...")
        
        # Import all models to ensure they're registered
        from app.models import (
            stock, options_data, user_preferences, analysis_results, 
            watchlist, precomputed_analysis
        )
        
        # Create all tables (this will only create new ones)
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database migration completed successfully!")
        logger.info("New tables created:")
        logger.info("- precomputed_analysis")
        logger.info("- precompute_job_status")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def verify_migration():
    """Verify that the migration was successful."""
    try:
        logger.info("Verifying migration...")
        
        # Test that we can query the new tables
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Test precomputed_analysis table
            count = db.query(PrecomputedAnalysis).count()
            logger.info(f"precomputed_analysis table: {count} records")
            
            # Test precompute_job_status table
            count = db.query(PrecomputeJobStatus).count()
            logger.info(f"precompute_job_status table: {count} records")
            
            logger.info("Migration verification successful!")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False


if __name__ == "__main__":
    print("BullsBears.xyz Precompute System Migration")
    print("=" * 50)
    
    # Run migration
    if run_migration():
        print("✅ Migration completed successfully!")
        
        # Verify migration
        if verify_migration():
            print("✅ Migration verification passed!")
            print("\nNext steps:")
            print("1. Update your .env file to enable precompute system:")
            print("   PRECOMPUTE_ENABLED=true")
            print("2. Restart your application services")
            print("3. Check the precompute status at: /api/v1/precompute/status")
            sys.exit(0)
        else:
            print("❌ Migration verification failed!")
            sys.exit(1)
    else:
        print("❌ Migration failed!")
        sys.exit(1)
