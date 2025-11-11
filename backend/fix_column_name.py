#!/usr/bin/env python3
"""
Fix column name in historical_data table
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.append('.')

from app.core.database import get_database

async def fix_column_name():
    """Fix the column name from adj_close to adjusted_close"""
    print("🔧 FIXING COLUMN NAME IN HISTORICAL_DATA TABLE")
    print("=" * 50)
    
    try:
        db = await get_database()
        
        # Check if adj_close column exists
        adj_close_exists = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'historical_data' 
                AND column_name = 'adj_close'
            )
        """)
        
        # Check if adjusted_close column exists
        adjusted_close_exists = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'historical_data' 
                AND column_name = 'adjusted_close'
            )
        """)
        
        print(f"adj_close column exists: {adj_close_exists}")
        print(f"adjusted_close column exists: {adjusted_close_exists}")
        
        if adj_close_exists and not adjusted_close_exists:
            print("🔄 Renaming adj_close to adjusted_close...")
            await db.execute("""
                ALTER TABLE historical_data 
                RENAME COLUMN adj_close TO adjusted_close
            """)
            print("✅ Column renamed successfully")
            
        elif adjusted_close_exists:
            print("✅ adjusted_close column already exists")
            
        else:
            print("❌ Neither column exists - this is unexpected")
            
        # Verify the final state
        columns = await db.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'historical_data'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 Current table schema:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_column_name())
