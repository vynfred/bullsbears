#!/usr/bin/env python3
"""
Database Migration Runner for B1.1: ML Performance Tracking Extension
Safely executes the ML performance columns migration with rollback capability
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLMigrationRunner:
    """Migration runner for ML performance tracking extension."""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal
        self.migration_file = backend_dir / "migrations" / "add_ml_performance_columns.sql"
        self.rollback_file = backend_dir / "migrations" / "rollback_ml_performance_columns.sql"
    
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met for migration."""
        try:
            # Check if migration file exists
            if not self.migration_file.exists():
                logger.error(f"Migration file not found: {self.migration_file}")
                return False
            
            # Check database connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                if not result.fetchone():
                    logger.error("Database connection test failed")
                    return False
            
            # Check if analysis_results table exists (SQLite compatible)
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='analysis_results'
                """))
                if not result.fetchone():
                    logger.error("analysis_results table not found")
                    return False
            
            logger.info("Prerequisites check passed")
            return True
            
        except Exception as e:
            logger.error(f"Prerequisites check failed: {e}")
            return False
    
    def backup_table(self) -> bool:
        """Create a backup of the analysis_results table."""
        try:
            backup_table_name = f"analysis_results_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with self.engine.connect() as conn:
                # Create backup table
                conn.execute(text(f"""
                    CREATE TABLE {backup_table_name} AS 
                    SELECT * FROM analysis_results
                """))
                conn.commit()
                
                # Verify backup
                result = conn.execute(text(f"SELECT COUNT(*) FROM {backup_table_name}"))
                backup_count = result.fetchone()[0]
                
                result = conn.execute(text("SELECT COUNT(*) FROM analysis_results"))
                original_count = result.fetchone()[0]
                
                if backup_count != original_count:
                    logger.error(f"Backup verification failed: {backup_count} != {original_count}")
                    return False
                
                logger.info(f"Created backup table: {backup_table_name} ({backup_count} rows)")
                return True
                
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
    
    def check_existing_columns(self) -> dict:
        """Check which ML columns already exist."""
        try:
            with self.engine.connect() as conn:
                # SQLite compatible column check
                result = conn.execute(text("PRAGMA table_info(analysis_results)"))
                all_columns = [row[1] for row in result.fetchall()]  # row[1] is column name

                ml_columns = [
                    'response_time_ms', 'cache_hit', 'ai_cost_cents',
                    'grok_analysis_time', 'deepseek_analysis_time', 'consensus_time',
                    'handoff_delta', 'ml_features', 'consensus_score',
                    'api_calls_count', 'data_sources_used', 'performance_tier'
                ]

                existing_columns = [col for col in ml_columns if col in all_columns]
                
                expected_columns = [
                    'response_time_ms', 'cache_hit', 'ai_cost_cents',
                    'grok_analysis_time', 'deepseek_analysis_time', 'consensus_time',
                    'handoff_delta', 'ml_features', 'consensus_score',
                    'api_calls_count', 'data_sources_used', 'performance_tier'
                ]
                
                missing_columns = [col for col in expected_columns if col not in existing_columns]
                
                logger.info(f"Existing ML columns: {existing_columns}")
                logger.info(f"Missing ML columns: {missing_columns}")
                
                return {
                    'existing': existing_columns,
                    'missing': missing_columns,
                    'needs_migration': len(missing_columns) > 0
                }
                
        except Exception as e:
            logger.error(f"Column check failed: {e}")
            return {'existing': [], 'missing': [], 'needs_migration': True}
    
    def run_migration(self) -> bool:
        """Execute the ML performance migration."""
        try:
            # Read migration SQL
            with open(self.migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Execute migration
            with self.engine.connect() as conn:
                # Execute the entire migration as one transaction
                try:
                    conn.execute(text(migration_sql))
                    conn.commit()
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.warning(f"Some objects already exist: {e}")
                    else:
                        raise e
                
                logger.info("Migration executed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify that the migration was successful."""
        try:
            with self.engine.connect() as conn:
                # Check all expected columns exist (SQLite compatible)
                result = conn.execute(text("PRAGMA table_info(analysis_results)"))
                all_columns = [row[1] for row in result.fetchall()]  # row[1] is column name

                expected_ml_columns = [
                    'response_time_ms', 'cache_hit', 'ai_cost_cents',
                    'grok_analysis_time', 'deepseek_analysis_time', 'consensus_time',
                    'handoff_delta', 'ml_features', 'consensus_score',
                    'api_calls_count', 'data_sources_used', 'performance_tier'
                ]

                found_columns = [col for col in expected_ml_columns if col in all_columns]
                if len(found_columns) < 12:  # Should have 12 new columns
                    logger.error(f"Migration verification failed: only {len(found_columns)} columns found")
                    logger.error(f"Missing columns: {set(expected_ml_columns) - set(found_columns)}")
                    return False

                # Check indexes exist (SQLite compatible)
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND tbl_name='analysis_results'
                      AND name LIKE 'idx_analysis_%'
                """))

                indexes = result.fetchall()
                if len(indexes) < 5:  # Should have at least 5 new indexes
                    logger.warning(f"Some indexes may be missing: only {len(indexes)} found")

                # Check views exist (SQLite compatible)
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='view' AND name IN ('ml_training_data', 'cost_monitoring_daily')
                """))

                views = result.fetchall()
                if len(views) < 2:
                    logger.warning(f"Some views may be missing: only {len(views)} found")

                logger.info("Migration verification passed")
                logger.info(f"Added columns: {found_columns}")
                logger.info(f"Added indexes: {[idx[0] for idx in indexes]}")
                logger.info(f"Added views: {[view[0] for view in views]}")

                return True
                
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
    
    def create_rollback_script(self) -> bool:
        """Create a rollback script for the migration."""
        try:
            rollback_sql = """-- Rollback script for ML Performance Tracking Migration
-- This script removes the ML performance columns and related objects

BEGIN;

-- Drop views
DROP VIEW IF EXISTS ml_training_data;
DROP VIEW IF EXISTS cost_monitoring_daily;

-- Drop indexes
DROP INDEX IF EXISTS idx_analysis_agreement_level;
DROP INDEX IF EXISTS idx_analysis_consensus_score;
DROP INDEX IF EXISTS idx_analysis_response_time;
DROP INDEX IF EXISTS idx_analysis_ai_cost;
DROP INDEX IF EXISTS idx_analysis_performance_tier;
DROP INDEX IF EXISTS idx_symbol_created_consensus;
DROP INDEX IF EXISTS idx_agreement_confidence_time;
DROP INDEX IF EXISTS idx_cost_analysis_daily;

-- Drop constraints
ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS check_performance_tier;
ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS check_ai_cost_positive;
ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS check_response_time_positive;

-- Drop columns
ALTER TABLE analysis_results 
DROP COLUMN IF EXISTS response_time_ms,
DROP COLUMN IF EXISTS cache_hit,
DROP COLUMN IF EXISTS ai_cost_cents,
DROP COLUMN IF EXISTS grok_analysis_time,
DROP COLUMN IF EXISTS deepseek_analysis_time,
DROP COLUMN IF EXISTS consensus_time,
DROP COLUMN IF EXISTS handoff_delta,
DROP COLUMN IF EXISTS ml_features,
DROP COLUMN IF EXISTS consensus_score,
DROP COLUMN IF EXISTS api_calls_count,
DROP COLUMN IF EXISTS data_sources_used,
DROP COLUMN IF EXISTS performance_tier;

COMMIT;
"""
            
            with open(self.rollback_file, 'w') as f:
                f.write(rollback_sql)
            
            logger.info(f"Created rollback script: {self.rollback_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create rollback script: {e}")
            return False

def main():
    """Main migration execution function."""
    logger.info("Starting B1.1 ML Performance Tracking Migration")
    
    runner = MLMigrationRunner()
    
    # Step 1: Check prerequisites
    if not runner.check_prerequisites():
        logger.error("Prerequisites check failed. Aborting migration.")
        return False
    
    # Step 2: Check existing columns
    column_status = runner.check_existing_columns()
    if not column_status['needs_migration']:
        logger.info("Migration not needed - all columns already exist")
        return True
    
    # Step 3: Create backup
    if not runner.backup_table():
        logger.error("Backup creation failed. Aborting migration.")
        return False
    
    # Step 4: Create rollback script
    if not runner.create_rollback_script():
        logger.warning("Rollback script creation failed, but continuing...")
    
    # Step 5: Run migration
    if not runner.run_migration():
        logger.error("Migration execution failed.")
        return False
    
    # Step 6: Verify migration
    if not runner.verify_migration():
        logger.error("Migration verification failed.")
        return False
    
    logger.info("B1.1 ML Performance Tracking Migration completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
