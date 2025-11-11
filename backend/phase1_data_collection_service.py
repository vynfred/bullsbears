#!/usr/bin/env python3
"""
PHASE 1: DATA COLLECTION SERVICE
FMP API + Google Cloud SQL ONLY
- Prime database with 90 days of data
- Schedule regular data updates
- NO RunPod involvement
"""

import os
import asyncio
import asyncpg
import requests
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class DataCollectionService:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.fmp_api_key = os.getenv('FMP_API_KEY')
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"
        
    async def connect_database(self):
        """Connect to Google Cloud SQL"""
        try:
            conn = await asyncpg.connect(self.database_url)
            return conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    async def create_tables(self):
        """Create database tables for data collection"""
        print("📋 Creating data collection tables...")
        
        create_sql = """
        -- Prime OHLC data (90 days historical)
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
        
        -- Symbols master table
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
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Real-time price updates
        CREATE TABLE IF NOT EXISTS current_prices (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            price DECIMAL(12,4),
            change_percent DECIMAL(8,4),
            volume BIGINT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol)
        );
        
        -- Data collection status tracking
        CREATE TABLE IF NOT EXISTS data_collection_status (
            id SERIAL PRIMARY KEY,
            collection_type VARCHAR(50) NOT NULL,
            last_run TIMESTAMP,
            status VARCHAR(20),
            records_processed INTEGER,
            error_message TEXT,
            UNIQUE(collection_type)
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_prime_ohlc_symbol_date ON prime_ohlc_90d(symbol, date);
        CREATE INDEX IF NOT EXISTS idx_symbols_tier ON symbols(tier);
        CREATE INDEX IF NOT EXISTS idx_current_prices_symbol ON current_prices(symbol);
        """
        
        conn = await self.connect_database()
        if conn:
            await conn.execute(create_sql)
            await conn.close()
            print("✅ Tables created successfully")
            return True
        return False
    
    def fetch_nasdaq_symbols(self):
        """Fetch NASDAQ symbols from FMP"""
        print("📈 Fetching NASDAQ symbols...")
        
        url = f"{self.fmp_base_url}/stock/list"
        params = {"apikey": self.fmp_api_key}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                all_symbols = response.json()
                nasdaq_symbols = [
                    s for s in all_symbols 
                    if s.get('exchange') == 'NASDAQ' and 
                    s.get('type') == 'stock' and
                    len(s.get('symbol', '')) <= 5
                ]
                print(f"✅ Found {len(nasdaq_symbols)} NASDAQ symbols")
                return nasdaq_symbols[:1700]  # ACTIVE tier limit
            return []
        except Exception as e:
            print(f"❌ Failed to fetch symbols: {e}")
            return []
    
    async def prime_90_day_data(self):
        """PRIME DATABASE: Load 90 days of historical data"""
        print("🚀 PRIMING DATABASE WITH 90 DAYS OF DATA")
        print("=" * 50)
        
        # Get symbols
        symbols = self.fetch_nasdaq_symbols()
        if not symbols:
            return False
        
        # Insert symbols
        conn = await self.connect_database()
        if not conn:
            return False
        
        # Insert symbols into master table
        for symbol in symbols:
            await conn.execute("""
                INSERT INTO symbols (symbol, name, exchange, sector, industry, market_cap, tier)
                VALUES ($1, $2, $3, $4, $5, $6, 'ACTIVE')
                ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    last_updated = CURRENT_TIMESTAMP
            """, symbol.get('symbol'), symbol.get('name'), symbol.get('exchange'),
                symbol.get('sector'), symbol.get('industry'), symbol.get('marketCap'))
        
        # Fetch 90 days of historical data
        total_records = 0
        for i, symbol in enumerate(symbols):
            symbol_name = symbol['symbol']
            print(f"Processing {symbol_name} ({i+1}/{len(symbols)})")
            
            # Get historical data
            historical_data = self.fetch_historical_data(symbol_name, 90)
            
            # Insert historical data
            for record in historical_data:
                try:
                    await conn.execute("""
                        INSERT INTO prime_ohlc_90d (symbol, date, open, high, low, close, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (symbol, date) DO NOTHING
                    """, symbol_name, record.get('date'),
                        float(record.get('open', 0)), float(record.get('high', 0)),
                        float(record.get('low', 0)), float(record.get('close', 0)),
                        int(record.get('volume', 0)))
                    total_records += 1
                except Exception as e:
                    print(f"⚠️ Error inserting {symbol_name}: {e}")
        
        # Update status
        await conn.execute("""
            INSERT INTO data_collection_status (collection_type, last_run, status, records_processed)
            VALUES ('90_day_prime', CURRENT_TIMESTAMP, 'completed', $1)
            ON CONFLICT (collection_type) DO UPDATE SET
                last_run = CURRENT_TIMESTAMP,
                status = 'completed',
                records_processed = $1
        """, total_records)
        
        await conn.close()
        
        print(f"🎉 DATABASE PRIMED!")
        print(f"   Symbols: {len(symbols)}")
        print(f"   Historical Records: {total_records}")
        
        return True
    
    def fetch_historical_data(self, symbol: str, days: int):
        """Fetch historical data for symbol"""
        url = f"{self.fmp_base_url}/historical-price-full/{symbol}"
        params = {"apikey": self.fmp_api_key, "timeseries": days}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('historical', [])
            return []
        except Exception as e:
            print(f"❌ Failed to fetch {symbol}: {e}")
            return []
    
    async def daily_data_update(self):
        """Daily data update - keep database fresh"""
        print("🔄 Running daily data update...")
        
        conn = await self.connect_database()
        if not conn:
            return
        
        # Get active symbols
        symbols = await conn.fetch("SELECT symbol FROM symbols WHERE tier = 'ACTIVE' AND is_active = true")
        
        updated_count = 0
        for symbol_row in symbols:
            symbol = symbol_row['symbol']
            
            # Get latest 5 days (to catch up on any missed days)
            historical_data = self.fetch_historical_data(symbol, 5)
            
            for record in historical_data:
                try:
                    await conn.execute("""
                        INSERT INTO prime_ohlc_90d (symbol, date, open, high, low, close, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (symbol, date) DO NOTHING
                    """, symbol, record.get('date'),
                        float(record.get('open', 0)), float(record.get('high', 0)),
                        float(record.get('low', 0)), float(record.get('close', 0)),
                        int(record.get('volume', 0)))
                    updated_count += 1
                except:
                    pass
        
        # Update status
        await conn.execute("""
            INSERT INTO data_collection_status (collection_type, last_run, status, records_processed)
            VALUES ('daily_update', CURRENT_TIMESTAMP, 'completed', $1)
            ON CONFLICT (collection_type) DO UPDATE SET
                last_run = CURRENT_TIMESTAMP,
                status = 'completed',
                records_processed = $1
        """, updated_count)
        
        await conn.close()
        print(f"✅ Daily update completed: {updated_count} records")
    
    def start_scheduled_updates(self):
        """Start scheduled data collection"""
        print("⏰ Starting scheduled data collection...")
        
        # Schedule daily updates at 6 AM ET
        schedule.every().day.at("06:00").do(lambda: asyncio.run(self.daily_data_update()))
        
        print("✅ Scheduler started - daily updates at 6:00 AM ET")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

async def main():
    """Main function - Phase 1 Data Collection"""
    print("🗄️ BULLSBEARS PHASE 1: DATA COLLECTION SERVICE")
    print("=" * 60)
    print("FMP API + Google Cloud SQL ONLY")
    print("NO RunPod involvement in this phase")
    print("=" * 60)
    
    service = DataCollectionService()
    
    # Create tables
    if not await service.create_tables():
        print("❌ Failed to create tables")
        return
    
    # Prime database with 90 days
    if not await service.prime_90_day_data():
        print("❌ Failed to prime database")
        return
    
    print("\n🎯 PHASE 1 COMPLETE!")
    print("✅ Database primed with 90 days of data")
    print("✅ Ready for Phase 2: RunPod Screener Agent")
    
    # Ask if user wants to start scheduled updates
    start_scheduler = input("\n🔄 Start daily data updates? (y/n): ")
    if start_scheduler.lower() == 'y':
        service.start_scheduled_updates()

if __name__ == "__main__":
    asyncio.run(main())
