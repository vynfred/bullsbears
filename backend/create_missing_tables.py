#!/usr/bin/env python3
"""
Create missing database tables for historical data collection
"""

import asyncio
import sys
sys.path.append('.')

from app.core.database import get_database

async def create_missing_tables():
    """Create historical_data, candidate_tracking, and market_data tables"""
    print("🗄️  CREATING MISSING DATABASE TABLES")
    print("=" * 50)
    
    try:
        db = await get_database()
        
        # 1. Historical Data Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS historical_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                date DATE NOT NULL,
                open_price DECIMAL(10,2) NOT NULL,
                high_price DECIMAL(10,2) NOT NULL,
                low_price DECIMAL(10,2) NOT NULL,
                close_price DECIMAL(10,2) NOT NULL,
                volume BIGINT NOT NULL,
                adj_close DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        print("✅ historical_data table created")
        
        # Create index for performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_historical_symbol_date 
            ON historical_data(symbol, date DESC)
        """)
        
        # 2. Candidate Tracking Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS candidate_tracking (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                agent_name VARCHAR(50) NOT NULL,
                prediction_type VARCHAR(20) NOT NULL,
                confidence DECIMAL(5,2) NOT NULL,
                target_price DECIMAL(10,2),
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                outcome VARCHAR(20) DEFAULT 'pending',
                outcome_price DECIMAL(10,2),
                outcome_date TIMESTAMP
            )
        """)
        print("✅ candidate_tracking table created")
        
        # 3. Market Data Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                price DECIMAL(10,2),
                change_percent DECIMAL(5,2),
                volume BIGINT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_source VARCHAR(20) DEFAULT 'FMP'
            )
        """)
        print("✅ market_data table created")
        
        # Create index for market data
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp 
            ON market_data(symbol, timestamp DESC)
        """)
        
        # Verify tables exist
        tables = ['historical_data', 'candidate_tracking', 'market_data']
        for table in tables:
            exists = await db.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            
            if exists:
                count = await db.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"✅ {table}: VERIFIED ({count} records)")
            else:
                print(f"❌ {table}: FAILED TO CREATE")
        
        print("\n🎉 ALL TABLES READY FOR DATA COLLECTION!")
        return True
        
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_missing_tables())