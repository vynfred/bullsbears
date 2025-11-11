#!/usr/bin/env python3
"""
RunPod Pod Database Setup Script
This script should be run directly on a RunPod Pod to:
1. Connect to Google Cloud SQL
2. Create database tables
3. Fetch data from FMP API
4. Prime the database
"""

import os
import asyncio
import asyncpg
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Database configuration
DATABASE_URL = "postgresql://postgres:%3C%24%3FFh%2AQNNmfJ0vTD@104.198.40.56:5432/postgres"
FMP_API_KEY = os.getenv('FMP_API_KEY', '7agprgSoUNdROMt6ZMpsfEv5Ls1mqqb4')
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

async def test_database_connection():
    """Test connection to Google Cloud SQL"""
    print("🔌 Testing Google Cloud SQL connection...")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        
        print(f"✅ Database connected: {version.split(',')[0]}")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def create_database_tables():
    """Create necessary database tables"""
    print("📋 Creating database tables...")
    
    create_tables_sql = """
    -- Create prime_ohlc_90d table for 90-day historical data
    CREATE TABLE IF NOT EXISTS prime_ohlc_90d (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(10) NOT NULL,
        date DATE NOT NULL,
        open DECIMAL(12,4),
        high DECIMAL(12,4),
        low DECIMAL(12,4),
        close DECIMAL(12,4),
        volume BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    );
    
    -- Create symbols table
    CREATE TABLE IF NOT EXISTS symbols (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(10) UNIQUE NOT NULL,
        name VARCHAR(255),
        exchange VARCHAR(50),
        sector VARCHAR(100),
        industry VARCHAR(100),
        market_cap BIGINT,
        tier VARCHAR(20) DEFAULT 'ALL',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_prime_ohlc_symbol_date ON prime_ohlc_90d(symbol, date);
    CREATE INDEX IF NOT EXISTS idx_symbols_tier ON symbols(tier);
    CREATE INDEX IF NOT EXISTS idx_symbols_active ON symbols(is_active);
    """
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(create_tables_sql)
        await conn.close()
        
        print("✅ Database tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def fetch_nasdaq_symbols():
    """Fetch NASDAQ symbols from FMP API"""
    print("📈 Fetching NASDAQ symbols from FMP...")
    
    url = f"{FMP_BASE_URL}/stock/list"
    params = {"apikey": FMP_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            all_symbols = response.json()
            
            # Filter for NASDAQ symbols
            nasdaq_symbols = [
                symbol for symbol in all_symbols 
                if symbol.get('exchange') == 'NASDAQ' and 
                symbol.get('type') == 'stock' and
                len(symbol.get('symbol', '')) <= 5  # Exclude complex symbols
            ]
            
            print(f"✅ Found {len(nasdaq_symbols)} NASDAQ symbols")
            return nasdaq_symbols[:1700]  # Limit to 1700 for ACTIVE tier
            
        else:
            print(f"❌ FMP API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Failed to fetch symbols: {e}")
        return []

async def insert_symbols(symbols: List[Dict]):
    """Insert symbols into database"""
    print(f"💾 Inserting {len(symbols)} symbols into database...")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        insert_sql = """
        INSERT INTO symbols (symbol, name, exchange, sector, industry, market_cap, tier)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (symbol) DO UPDATE SET
            name = EXCLUDED.name,
            exchange = EXCLUDED.exchange,
            sector = EXCLUDED.sector,
            industry = EXCLUDED.industry,
            market_cap = EXCLUDED.market_cap,
            tier = EXCLUDED.tier,
            updated_at = CURRENT_TIMESTAMP
        """
        
        for symbol in symbols:
            await conn.execute(
                insert_sql,
                symbol.get('symbol'),
                symbol.get('name'),
                symbol.get('exchange'),
                symbol.get('sector'),
                symbol.get('industry'),
                symbol.get('marketCap'),
                'ACTIVE'
            )
        
        await conn.close()
        print("✅ Symbols inserted successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to insert symbols: {e}")
        return False

def fetch_historical_data(symbol: str, days: int = 90):
    """Fetch historical data for a symbol"""
    
    url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
    params = {
        "apikey": FMP_API_KEY,
        "timeseries": days
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            historical = data.get('historical', [])
            return historical
        else:
            return []
            
    except Exception as e:
        print(f"❌ Failed to fetch data for {symbol}: {e}")
        return []

async def prime_historical_data(symbols: List[str], batch_size: int = 50):
    """Prime database with 90 days of historical data"""
    print(f"📊 Priming historical data for {len(symbols)} symbols...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    insert_sql = """
    INSERT INTO prime_ohlc_90d (symbol, date, open, high, low, close, volume)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, date) DO NOTHING
    """
    
    total_records = 0
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(symbols) + batch_size - 1)//batch_size}")
        
        for symbol in batch:
            historical_data = fetch_historical_data(symbol)
            
            for record in historical_data:
                try:
                    await conn.execute(
                        insert_sql,
                        symbol,
                        record.get('date'),
                        float(record.get('open', 0)),
                        float(record.get('high', 0)),
                        float(record.get('low', 0)),
                        float(record.get('close', 0)),
                        int(record.get('volume', 0))
                    )
                    total_records += 1
                except Exception as e:
                    print(f"⚠️ Failed to insert {symbol} {record.get('date')}: {e}")
    
    await conn.close()
    print(f"✅ Inserted {total_records} historical records")
    return total_records

async def main():
    """Main database priming function"""
    print("🚀 BULLSBEARS DATABASE PRIMING ON RUNPOD")
    print("=" * 50)
    
    # Step 1: Test database connection
    if not await test_database_connection():
        print("❌ Cannot proceed without database connection")
        return False
    
    # Step 2: Create tables
    if not await create_database_tables():
        print("❌ Cannot proceed without database tables")
        return False
    
    # Step 3: Fetch symbols
    symbols = fetch_nasdaq_symbols()
    if not symbols:
        print("❌ Cannot proceed without symbols")
        return False
    
    # Step 4: Insert symbols
    if not await insert_symbols(symbols):
        print("❌ Failed to insert symbols")
        return False
    
    # Step 5: Prime historical data
    symbol_list = [s['symbol'] for s in symbols]
    records_inserted = await prime_historical_data(symbol_list)
    
    print("\n🎉 DATABASE PRIMING COMPLETED!")
    print(f"📊 Results:")
    print(f"   Symbols: {len(symbols)}")
    print(f"   Historical Records: {records_inserted}")
    print(f"   Database: Google Cloud SQL")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
