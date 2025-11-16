#!/usr/bin/env python3
"""
Comprehensive database verification for 100% readiness
Verifies all tables, columns, indexes, and seed data
"""

import asyncio
import asyncpg
from datetime import date

DB_CONFIG = {
    'host': '104.198.40.56',
    'user': 'postgres',
    'password': '<$?Fh*QNNmfJ0vTD',
    'database': 'postgres'
}

async def verify_database():
    """Comprehensive database verification"""
    
    print("🔍 BullsBears Database 100% Verification\n")
    print("=" * 60)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    all_checks_passed = True
    
    # 1. Core Tables
    print("\n📊 CORE TABLES")
    core_tables = [
        'picks', 'scan_errors', 'agent_performance', 'market_conditions',
        'social_sentiment', 'learning_cycles', 'prompt_updates', 'trending_stocks'
    ]
    for table in core_tables:
        exists = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')")
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")
        if not exists:
            all_checks_passed = False
    
    # 2. Learning System Tables
    print("\n🧠 LEARNING SYSTEM TABLES")
    learning_tables = [
        'feature_weights', 'agent_weights', 'arbitrator_decisions',
        'confidence_factors', 'learning_feedback', 'prompt_examples', 'model_weights'
    ]
    for table in learning_tables:
        exists = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')")
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")
        if not exists:
            all_checks_passed = False
    
    # 3. Outcome Tracking Tables
    print("\n📈 OUTCOME TRACKING TABLES")
    outcome_tables = ['shortlist_candidates', 'pick_outcomes_detailed']
    for table in outcome_tables:
        exists = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')")
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")
        if not exists:
            all_checks_passed = False
    
    # 4. Critical Columns
    print("\n🔧 CRITICAL COLUMNS")
    
    # picks.pick_context
    pick_context_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'picks' AND column_name = 'pick_context'
        )
    """)
    status = "✅" if pick_context_exists else "❌"
    print(f"   {status} picks.pick_context (JSONB)")
    if not pick_context_exists:
        all_checks_passed = False
    
    # shortlist_candidates columns
    shortlist_columns = [
        'prescreen_score', 'price_at_selection', 'technical_snapshot',
        'fundamental_snapshot', 'vision_flags', 'vision_analysis_text', 'social_data'
    ]
    for col in shortlist_columns:
        exists = await conn.fetchval(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'shortlist_candidates' AND column_name = '{col}'
            )
        """)
        status = "✅" if exists else "❌"
        print(f"   {status} shortlist_candidates.{col}")
        if not exists:
            all_checks_passed = False
    
    # 5. Seed Data
    print("\n🌱 SEED DATA")
    
    feature_weights_count = await conn.fetchval("SELECT COUNT(*) FROM feature_weights")
    status = "✅" if feature_weights_count >= 10 else "❌"
    print(f"   {status} feature_weights: {feature_weights_count} records (expected >= 10)")
    if feature_weights_count < 10:
        all_checks_passed = False
    
    agent_weights_count = await conn.fetchval("SELECT COUNT(*) FROM agent_weights")
    status = "✅" if agent_weights_count >= 6 else "❌"
    print(f"   {status} agent_weights: {agent_weights_count} records (expected >= 6)")
    if agent_weights_count < 6:
        all_checks_passed = False
    
    agent_performance_count = await conn.fetchval("SELECT COUNT(*) FROM agent_performance")
    status = "✅" if agent_performance_count >= 7 else "❌"
    print(f"   {status} agent_performance: {agent_performance_count} records (expected >= 7)")
    if agent_performance_count < 7:
        all_checks_passed = False
    
    # 6. Indexes
    print("\n📇 CRITICAL INDEXES")
    critical_indexes = [
        ('shortlist_candidates', 'idx_shortlist_date_symbol'),
        ('shortlist_candidates', 'idx_shortlist_selected'),
        ('picks', 'idx_picks_ticker'),
        ('arbitrator_decisions', 'idx_arbitrator_final_pick'),
    ]
    for table, index in critical_indexes:
        exists = await conn.fetchval(f"""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = '{table}' AND indexname = '{index}'
            )
        """)
        status = "✅" if exists else "❌"
        print(f"   {status} {table}.{index}")
        if not exists:
            all_checks_passed = False
    
    # 7. Total Table Count
    print("\n📊 DATABASE SUMMARY")
    total_tables = await conn.fetchval("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
    print(f"   Total tables: {total_tables}")
    
    await conn.close()
    
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ DATABASE IS 100% READY FOR PRODUCTION!")
    else:
        print("❌ DATABASE HAS ISSUES - SEE ABOVE")
    print("=" * 60)
    
    return all_checks_passed

if __name__ == "__main__":
    result = asyncio.run(verify_database())
    exit(0 if result else 1)

