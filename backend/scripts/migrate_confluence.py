#!/usr/bin/env python3
"""
Migration: Add confluence targeting columns to picks and pick_outcomes_detailed tables
BullsBears v5 - Full Confluence Target System

Run: python -m scripts.migrate_confluence
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_migration():
    """Add confluence columns to database tables"""
    print("=" * 60)
    print("BullsBears v5 - Confluence System Migration")
    print("=" * 60)
    
    from app.core.database import get_asyncpg_pool
    
    try:
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            
            # ==================== PICKS TABLE ====================
            print("\n[1/2] Migrating picks table...")
            
            # Add confluence_score
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS confluence_score SMALLINT DEFAULT 0
            """)
            print("  ✓ Added confluence_score")
            
            # Add confluence_methods (array of method names)
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS confluence_methods TEXT[] DEFAULT '{}'
            """)
            print("  ✓ Added confluence_methods")
            
            # Add rsi_divergence
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS rsi_divergence BOOLEAN DEFAULT FALSE
            """)
            print("  ✓ Added rsi_divergence")
            
            # Add primary_target (replaces target_low logic)
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS primary_target NUMERIC(10, 2)
            """)
            print("  ✓ Added primary_target")
            
            # Add moonshot_target (nullable - only shown when conditions met)
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS moonshot_target NUMERIC(10, 2)
            """)
            print("  ✓ Added moonshot_target")
            
            # Add gann_alignment
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS gann_alignment BOOLEAN DEFAULT FALSE
            """)
            print("  ✓ Added gann_alignment")
            
            # Add weekly pivot data for chart rendering
            await conn.execute("""
                ALTER TABLE picks 
                ADD COLUMN IF NOT EXISTS weekly_pivots JSONB
            """)
            print("  ✓ Added weekly_pivots (R1/R2/S1/S2)")
            
            # ==================== PICK_OUTCOMES_DETAILED TABLE ====================
            print("\n[2/2] Migrating pick_outcomes_detailed table...")
            
            # Add confluence_score
            await conn.execute("""
                ALTER TABLE pick_outcomes_detailed 
                ADD COLUMN IF NOT EXISTS confluence_score SMALLINT
            """)
            print("  ✓ Added confluence_score")
            
            # Add hit_primary_target
            await conn.execute("""
                ALTER TABLE pick_outcomes_detailed 
                ADD COLUMN IF NOT EXISTS hit_primary_target BOOLEAN DEFAULT FALSE
            """)
            print("  ✓ Added hit_primary_target")
            
            # Add hit_moonshot_target
            await conn.execute("""
                ALTER TABLE pick_outcomes_detailed 
                ADD COLUMN IF NOT EXISTS hit_moonshot_target BOOLEAN DEFAULT FALSE
            """)
            print("  ✓ Added hit_moonshot_target")
            
            # Add primary_target and moonshot_target for outcome tracking
            await conn.execute("""
                ALTER TABLE pick_outcomes_detailed 
                ADD COLUMN IF NOT EXISTS primary_target NUMERIC(10, 2)
            """)
            await conn.execute("""
                ALTER TABLE pick_outcomes_detailed 
                ADD COLUMN IF NOT EXISTS moonshot_target NUMERIC(10, 2)
            """)
            print("  ✓ Added primary_target and moonshot_target")
            
            print("\n" + "=" * 60)
            print("✅ MIGRATION COMPLETE - Confluence columns added")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)

