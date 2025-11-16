#!/usr/bin/env python3
"""
One-time migration script to add user_id to existing watchlist entries
Run this once when deploying Firebase Auth
"""

import asyncio
import asyncpg
import os
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env!")


async def migrate_watchlist():
    """Add user_id column to watchlist table and set default user"""
    
    print("🔄 Starting watchlist migration...")
    
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check if user_id column already exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'watchlist' 
                AND column_name = 'user_id'
            )
        """)
        
        if column_exists:
            print("✅ user_id column already exists")
        else:
            print("📝 Adding user_id column to watchlist table...")
            
            # Add user_id column (nullable initially)
            await conn.execute("""
                ALTER TABLE watchlist 
                ADD COLUMN user_id VARCHAR(128)
            """)
            
            print("✅ user_id column added")
        
        # Count existing entries without user_id
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM watchlist WHERE user_id IS NULL
        """)
        
        if count > 0:
            print(f"📊 Found {count} watchlist entries without user_id")
            print("⚠️  These entries need to be assigned to a user manually")
            print("   Option 1: Delete them (if test data)")
            print("   Option 2: Assign to a default user ID")
            
            # For now, we'll just report them
            entries = await conn.fetch("""
                SELECT id, symbol, entry_price, added_at 
                FROM watchlist 
                WHERE user_id IS NULL
                LIMIT 10
            """)
            
            print("\n📋 Sample entries:")
            for entry in entries:
                print(f"   ID: {entry['id']}, Symbol: {entry['symbol']}, "
                      f"Entry: ${entry['entry_price']}, Added: {entry['added_at']}")
            
            if count > 10:
                print(f"   ... and {count - 10} more")
        else:
            print("✅ All watchlist entries have user_id")
        
        # Create index on user_id for performance
        index_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM pg_indexes 
                WHERE tablename = 'watchlist' 
                AND indexname = 'idx_watchlist_user_id'
            )
        """)
        
        if not index_exists:
            print("📝 Creating index on user_id...")
            await conn.execute("""
                CREATE INDEX idx_watchlist_user_id ON watchlist(user_id)
            """)
            print("✅ Index created")
        else:
            print("✅ Index already exists")
        
        # Make user_id NOT NULL after migration (optional - uncomment when ready)
        # await conn.execute("""
        #     ALTER TABLE watchlist 
        #     ALTER COLUMN user_id SET NOT NULL
        # """)
        
        print("\n✅ Migration complete!")
        print("⚠️  Remember to update API endpoints to require user authentication")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()


async def delete_test_data():
    """Delete all watchlist entries without user_id (test data cleanup)"""
    
    print("🗑️  Deleting test watchlist data...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        count = await conn.fetchval("""
            DELETE FROM watchlist WHERE user_id IS NULL
            RETURNING COUNT(*)
        """)
        
        print(f"✅ Deleted {count} test entries")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        raise
    finally:
        await conn.close()


async def assign_default_user(default_user_id: str):
    """Assign all entries without user_id to a default user"""
    
    print(f"👤 Assigning entries to default user: {default_user_id}")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        count = await conn.fetchval("""
            UPDATE watchlist 
            SET user_id = $1 
            WHERE user_id IS NULL
            RETURNING COUNT(*)
        """, default_user_id)
        
        print(f"✅ Assigned {count} entries to user {default_user_id}")
        
    except Exception as e:
        print(f"❌ Assignment failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "delete":
            asyncio.run(delete_test_data())
        elif command == "assign" and len(sys.argv) > 2:
            user_id = sys.argv[2]
            asyncio.run(assign_default_user(user_id))
        else:
            print("Usage:")
            print("  python migrate_watchlist_to_user_specific.py          # Run migration")
            print("  python migrate_watchlist_to_user_specific.py delete   # Delete test data")
            print("  python migrate_watchlist_to_user_specific.py assign <user_id>  # Assign to user")
    else:
        asyncio.run(migrate_watchlist())

