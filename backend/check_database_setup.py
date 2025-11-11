#!/usr/bin/env python3
"""
Check database setup and create tables if needed
"""

import asyncio
import logging
from app.core.database import get_database

async def check_database_setup():
    """Check if all required tables exist and create if missing"""
    print("🔍 CHECKING DATABASE SETUP")
    print("=" * 50)
    
    try:
        db = await get_database()
        
        # Check if main tables exist
        tables_to_check = [
            'stock_classifications',
            'historical_data', 
            'picks',
            'candidate_tracking',
            'market_data'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in tables_to_check:
            result = await db.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            
            if result:
                existing_tables.append(table)
                # Get row count
                count = await db.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"✅ {table}: EXISTS ({count} records)")
            else:
                missing_tables.append(table)
                print(f"❌ {table}: MISSING")
        
        if missing_tables:
            print(f"\n🔧 MISSING TABLES: {missing_tables}")
            print("Run database migrations first:")
            print("cd backend && python manage_database.py")
            return False
        else:
            print(f"\n✅ ALL TABLES READY: {len(existing_tables)}/5")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Check PostgreSQL is running and DATABASE_URL is correct")
        return False

if __name__ == "__main__":
    asyncio.run(check_database_setup())