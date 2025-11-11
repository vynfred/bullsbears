#!/usr/bin/env python3
"""
Simple direct database connection test
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    """Test database connection directly"""
    
    database_url = os.getenv('DATABASE_URL')
    print(f"🔌 Testing connection to: {database_url[:50]}...")
    
    try:
        # Test connection with timeout
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=10.0
        )
        
        print("✅ Connection successful!")
        
        # Test basic query
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL: {version.split(',')[0]}")
        
        # List tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"\n📋 Tables found: {len(tables)}")
        for table in tables[:10]:  # Show first 10
            print(f"   - {table['table_name']}")
        
        await conn.close()
        return True
        
    except asyncio.TimeoutError:
        print("❌ Connection timeout - check network/firewall")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        print("\n🎉 Database is ready!")
    else:
        print("\n🔧 Database connection needs troubleshooting")
