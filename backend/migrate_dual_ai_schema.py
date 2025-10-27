#!/usr/bin/env python3
"""
Database migration script to add dual AI scoring columns for ML training data collection.
Extends existing tables with Grok/DeepSeek consensus scoring and agreement tracking.

Usage: python migrate_dual_ai_schema.py
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, inspect
from app.core.database import engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL migration statements for dual AI scoring columns (SQLite compatible)
MIGRATION_STATEMENTS = [
    # Add dual AI scoring columns to analysis_results table (one by one for SQLite)
    "ALTER TABLE analysis_results ADD COLUMN grok_score REAL",
    "ALTER TABLE analysis_results ADD COLUMN deepseek_score REAL",
    "ALTER TABLE analysis_results ADD COLUMN agreement_level TEXT",
    "ALTER TABLE analysis_results ADD COLUMN confidence_adjustment REAL",
    "ALTER TABLE analysis_results ADD COLUMN hybrid_validation_triggered INTEGER DEFAULT 0",
    "ALTER TABLE analysis_results ADD COLUMN consensus_reasoning TEXT",
    "ALTER TABLE analysis_results ADD COLUMN social_news_bridge REAL",
    "ALTER TABLE analysis_results ADD COLUMN dual_ai_version TEXT DEFAULT '1.0'",

    # Add dual AI scoring columns to precomputed_analysis table
    "ALTER TABLE precomputed_analysis ADD COLUMN grok_confidence REAL",
    "ALTER TABLE precomputed_analysis ADD COLUMN deepseek_sentiment REAL",
    "ALTER TABLE precomputed_analysis ADD COLUMN ai_agreement_level TEXT",
    "ALTER TABLE precomputed_analysis ADD COLUMN consensus_confidence_boost REAL",
    "ALTER TABLE precomputed_analysis ADD COLUMN hybrid_validation_used INTEGER DEFAULT 0",
    "ALTER TABLE precomputed_analysis ADD COLUMN dual_ai_reasoning TEXT",
    "ALTER TABLE precomputed_analysis ADD COLUMN ai_model_versions TEXT", # JSON as TEXT in SQLite

    # Add dual AI scoring columns to chosen_options table for tracking user selections
    "ALTER TABLE chosen_options ADD COLUMN grok_technical_score REAL",
    "ALTER TABLE chosen_options ADD COLUMN deepseek_sentiment_score REAL",
    "ALTER TABLE chosen_options ADD COLUMN ai_consensus_level TEXT",
    "ALTER TABLE chosen_options ADD COLUMN confidence_boost_applied REAL",
    "ALTER TABLE chosen_options ADD COLUMN hybrid_validation_outcome INTEGER",
    "ALTER TABLE chosen_options ADD COLUMN dual_ai_recommendation_reasoning TEXT",
    "ALTER TABLE chosen_options ADD COLUMN ai_analysis_timestamp TEXT", # TIMESTAMP as TEXT in SQLite

    # Create a dedicated table for detailed dual AI training data (SQLite compatible)
    """
    CREATE TABLE IF NOT EXISTS dual_ai_training_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_result_id INTEGER REFERENCES analysis_results(id),
        symbol TEXT NOT NULL,

        -- Grok AI Analysis Data
        grok_recommendation TEXT,
        grok_confidence REAL,
        grok_reasoning TEXT,
        grok_risk_warning TEXT,
        grok_key_factors TEXT, -- JSON as TEXT in SQLite
        grok_response_time_ms INTEGER,

        -- DeepSeek AI Analysis Data
        deepseek_sentiment_score REAL,
        deepseek_confidence REAL,
        deepseek_narrative TEXT,
        deepseek_key_themes TEXT, -- JSON as TEXT in SQLite
        deepseek_crowd_psychology TEXT,
        deepseek_sarcasm_detected INTEGER, -- BOOLEAN as INTEGER in SQLite
        deepseek_social_news_bridge REAL,
        deepseek_response_time_ms INTEGER,

        -- Consensus Engine Data
        consensus_recommendation TEXT,
        consensus_confidence REAL,
        agreement_level TEXT,
        confidence_adjustment REAL,
        hybrid_validation_triggered INTEGER, -- BOOLEAN as INTEGER in SQLite
        consensus_reasoning TEXT,

        -- ML Training Metadata
        training_label TEXT, -- For supervised learning (CORRECT, INCORRECT, PARTIAL)
        actual_outcome REAL, -- Actual stock/option performance
        outcome_timestamp TEXT, -- TIMESTAMP as TEXT in SQLite
        data_quality_score REAL DEFAULT 100.0,

        -- Technical Context for ML Features
        market_conditions TEXT, -- JSON as TEXT in SQLite
        technical_indicators TEXT, -- JSON as TEXT in SQLite
        news_context TEXT, -- JSON as TEXT in SQLite
        social_context TEXT, -- JSON as TEXT in SQLite

        -- Timestamps
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """,

    # Create indexes for performance on dual AI columns (after columns are added)
    "CREATE INDEX IF NOT EXISTS idx_analysis_results_grok_score ON analysis_results(grok_score)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_results_agreement_level ON analysis_results(agreement_level)",
    "CREATE INDEX IF NOT EXISTS idx_precomputed_analysis_ai_agreement ON precomputed_analysis(ai_agreement_level)",
    "CREATE INDEX IF NOT EXISTS idx_chosen_options_consensus_level ON chosen_options(ai_consensus_level)",

    # Create indexes for the training data table
    "CREATE INDEX IF NOT EXISTS idx_dual_ai_training_symbol ON dual_ai_training_data(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_dual_ai_training_agreement ON dual_ai_training_data(agreement_level)",
    "CREATE INDEX IF NOT EXISTS idx_dual_ai_training_label ON dual_ai_training_data(training_label)",
    "CREATE INDEX IF NOT EXISTS idx_dual_ai_training_created ON dual_ai_training_data(created_at)"
]

def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error checking table existence: {e}")
        return False

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"Error checking column existence: {e}")
        return False

def run_migration():
    """Execute the dual AI schema migration."""
    logger.info("🚀 Starting Dual AI Schema Migration...")
    logger.info("=" * 60)

    # Check database connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

    # Check required tables exist
    required_tables = ['analysis_results', 'precomputed_analysis', 'chosen_options']
    for table in required_tables:
        if not check_table_exists(table):
            logger.error(f"❌ Required table '{table}' does not exist")
            return False
        logger.info(f"✅ Table '{table}' exists")

    # Execute migration statements with better error handling
    success_count = 0
    total_statements = len(MIGRATION_STATEMENTS)

    with engine.begin() as conn:
        for i, statement in enumerate(MIGRATION_STATEMENTS, 1):
            try:
                logger.info(f"📝 Executing migration {i}/{total_statements}...")

                # Skip if it's an ADD COLUMN and column already exists
                if "ADD COLUMN" in statement:
                    table_name = statement.split("ALTER TABLE ")[1].split(" ADD COLUMN")[0].strip()
                    column_name = statement.split("ADD COLUMN ")[1].split(" ")[0].strip()
                    if check_column_exists(table_name, column_name):
                        logger.info(f"⏭️ Column {table_name}.{column_name} already exists, skipping")
                        success_count += 1
                        continue

                conn.execute(text(statement))
                success_count += 1
                logger.info(f"✅ Migration {i}/{total_statements} completed")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info(f"⏭️ Migration {i}/{total_statements} skipped (already exists)")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ Migration {i}/{total_statements} failed: {e}")
                continue
    
    # Verify key columns were added
    logger.info("\n🔍 Verifying migration results...")
    
    verification_checks = [
        ('analysis_results', 'grok_score'),
        ('analysis_results', 'deepseek_score'),
        ('analysis_results', 'agreement_level'),
        ('precomputed_analysis', 'grok_confidence'),
        ('precomputed_analysis', 'deepseek_sentiment'),
        ('chosen_options', 'grok_technical_score'),
    ]
    
    verified_count = 0
    for table, column in verification_checks:
        if check_column_exists(table, column):
            logger.info(f"✅ Column '{table}.{column}' verified")
            verified_count += 1
        else:
            logger.warning(f"⚠️ Column '{table}.{column}' not found")
    
    # Check if training data table was created
    if check_table_exists('dual_ai_training_data'):
        logger.info("✅ Table 'dual_ai_training_data' created successfully")
        verified_count += 1
    else:
        logger.warning("⚠️ Table 'dual_ai_training_data' not found")
    
    # Migration summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 DUAL AI SCHEMA MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Migration Statements: {success_count}/{total_statements}")
    logger.info(f"✅ Verification Checks: {verified_count}/{len(verification_checks) + 1}")
    
    if verified_count >= len(verification_checks):
        logger.info("🎉 Migration completed successfully!")
        logger.info("\n📋 New ML Training Capabilities:")
        logger.info("   • Grok AI scoring and confidence tracking")
        logger.info("   • DeepSeek sentiment analysis scoring")
        logger.info("   • AI agreement level classification")
        logger.info("   • Confidence adjustment tracking")
        logger.info("   • Hybrid validation outcome logging")
        logger.info("   • Dedicated training data table with labels")
        logger.info("   • Performance indexes for ML queries")
        return True
    else:
        logger.warning("⚠️ Migration completed with some issues")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
