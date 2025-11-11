#!/usr/bin/env python3
"""
Test Google Cloud SQL Database Connection
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def test_database_connection():
    """Test connection to Google Cloud SQL PostgreSQL"""
    
    # Get database credentials from .env
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print(f"Using DATABASE_URL: {database_url[:50]}...")
        connection_string = database_url
    else:
        # Fallback to individual components
        host = os.getenv('DATABASE_HOST', '104.198.40.56')
        port = os.getenv('DATABASE_PORT', '5432')
        database = os.getenv('DATABASE_NAME', 'postgres')
        user = os.getenv('DATABASE_USER', 'postgres')
        password = os.getenv('DATABASE_PASSWORD', '<$?Fh*QNNmfJ0vTD')

        print("🗄️ Google Cloud SQL Connection Test")
        print("=" * 50)
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Database: {database}")
        print(f"User: {user}")
        print(f"Password: {'*' * len(password) if password else 'None'}")

        # Build connection string with URL encoding for password
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(password)
        connection_string = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
    

    
    try:
        print("\n🔌 Attempting connection...")
        
        # Test connection
        conn = await asyncpg.connect(connection_string)
        
        print("✅ Connection successful!")
        
        # Test basic query
        print("\n🔍 Testing basic queries...")
        
        # Get PostgreSQL version
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL Version: {version.split(',')[0]}")
        
        # List existing tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"\n📋 Existing tables ({len(tables)}):")
        if tables:
            for table in tables:
                print(f"   - {table['table_name']}")
        else:
            print("   (No tables found - database is empty)")
        
        # Test write permissions
        print("\n✏️ Testing write permissions...")
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS connection_test (
                    id SERIAL PRIMARY KEY,
                    test_time TIMESTAMP DEFAULT NOW(),
                    message TEXT
                )
            """)
            
            await conn.execute("""
                INSERT INTO connection_test (message) 
                VALUES ('BullsBears connection test')
            """)
            
            test_count = await conn.fetchval("""
                SELECT COUNT(*) FROM connection_test
            """)
            
            print(f"✅ Write test successful - {test_count} test records")
            
            # Clean up test table
            await conn.execute("DROP TABLE IF EXISTS connection_test")
            print("🧹 Test table cleaned up")
            
        except Exception as e:
            print(f"⚠️ Write test failed: {e}")
        
        await conn.close()
        
        print("\n" + "=" * 50)
        print("🎉 DATABASE CONNECTION SUCCESSFUL!")
        print("✅ Ready to run migrations and bootstrap data")
        
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ Authentication failed - check username/password")
        return False
    except asyncpg.exceptions.InvalidCatalogNameError:
        print("❌ Database not found - check database name")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Possible issues:")
        print("   - Check if Google Cloud SQL instance is running")
        print("   - Verify IP address is whitelisted")
        print("   - Confirm database credentials")
        print("   - Check network connectivity")
        return False

async def main():
    """Main test function"""
    success = await test_database_connection()
    
    if success:
        print("\n🚀 NEXT STEPS:")
        print("1. Run database migrations:")
        print("   python run_bootstrap.py migrate")
        print("2. Start admin dashboard")
        print("3. Bootstrap historical data")
    else:
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Check Google Cloud SQL console")
        print("2. Verify instance is running")
        print("3. Check authorized networks")
        print("4. Confirm database exists")

if __name__ == "__main__":
    asyncio.run(main())
