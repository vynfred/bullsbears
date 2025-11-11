#!/usr/bin/env python3
"""
Load NASDAQ symbols from CSV into surveillance database
Prepares the foundation for the rolling surveillance system
"""

import asyncio
import asyncpg
import pandas as pd
import logging
from datetime import datetime
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NASDAQSymbolLoader:
    """Load NASDAQ symbols from CSV into PostgreSQL database"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://vynfred@localhost:5432/bullsbears')
        self.csv_path = '/Users/vynfred/Documents/bullsbears/Data/nasdaq_screener_1762100638908.csv'
        
    async def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = await asyncpg.connect(self.db_url)
            logger.info("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def close_db(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            await self.conn.close()
            logger.info("✅ Database connection closed")
    
    async def create_tables(self):
        """Create surveillance tables if they don't exist"""
        try:
            # Read and execute the migration SQL
            migration_path = Path(__file__).parent.parent / 'database' / 'migrations' / '007_create_surveillance_tables.sql'
            
            with open(migration_path, 'r') as f:
                sql_content = f.read()
            
            await self.conn.execute(sql_content)
            logger.info("✅ Surveillance tables created/verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            return False
    
    def load_nasdaq_csv(self):
        """Load NASDAQ symbols from CSV file"""
        try:
            logger.info(f"📊 Loading NASDAQ symbols from: {self.csv_path}")
            
            # Read CSV with proper data types
            df = pd.read_csv(self.csv_path)
            
            logger.info(f"📈 Loaded {len(df)} symbols from CSV")
            logger.info(f"📋 Columns: {list(df.columns)}")
            
            # Clean and prepare data
            df = self.clean_nasdaq_data(df)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error loading CSV: {e}")
            return None
    
    def clean_nasdaq_data(self, df):
        """Clean and prepare NASDAQ data for database insertion"""
        logger.info("🧹 Cleaning NASDAQ data...")
        
        # Remove any rows with missing symbols
        df = df.dropna(subset=['Symbol'])
        
        # Clean symbol column (remove any whitespace)
        df['Symbol'] = df['Symbol'].str.strip().str.upper()
        
        # Clean market cap - convert to numeric, handle missing values
        df['Market Cap'] = df['Market Cap'].replace('', 0)
        df['Market Cap'] = pd.to_numeric(df['Market Cap'], errors='coerce').fillna(0)
        
        # Clean IPO Year
        df['IPO Year'] = pd.to_numeric(df['IPO Year'], errors='coerce')
        
        # Clean text fields
        df['Name'] = df['Name'].fillna('Unknown Company')
        df['Country'] = df['Country'].fillna('Unknown')
        df['Sector'] = df['Sector'].fillna('Unknown')
        df['Industry'] = df['Industry'].fillna('Unknown')
        
        # Remove duplicates based on symbol
        initial_count = len(df)
        df = df.drop_duplicates(subset=['Symbol'], keep='first')
        final_count = len(df)
        
        if initial_count != final_count:
            logger.info(f"🔄 Removed {initial_count - final_count} duplicate symbols")
        
        logger.info(f"✅ Cleaned data: {len(df)} unique symbols ready for insertion")
        
        return df
    
    async def insert_nasdaq_symbols(self, df):
        """Insert NASDAQ symbols into database"""
        try:
            logger.info("💾 Inserting NASDAQ symbols into database...")
            
            # Prepare data for insertion
            symbols_data = []
            for _, row in df.iterrows():
                symbol_record = (
                    row['Symbol'],
                    row['Name'],
                    int(row['Market Cap']) if pd.notna(row['Market Cap']) else None,
                    row['Country'],
                    int(row['IPO Year']) if pd.notna(row['IPO Year']) else None,
                    row['Sector'],
                    row['Industry']
                )
                symbols_data.append(symbol_record)
            
            # Insert with ON CONFLICT handling (upsert)
            insert_query = """
                INSERT INTO nasdaq_symbols (symbol, name, market_cap, country, ipo_year, sector, industry)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (symbol) 
                DO UPDATE SET
                    name = EXCLUDED.name,
                    market_cap = EXCLUDED.market_cap,
                    country = EXCLUDED.country,
                    ipo_year = EXCLUDED.ipo_year,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    updated_at = NOW()
            """
            
            # Execute batch insert
            await self.conn.executemany(insert_query, symbols_data)
            
            logger.info(f"✅ Successfully inserted/updated {len(symbols_data)} NASDAQ symbols")
            
            # Verify insertion
            count_query = "SELECT COUNT(*) FROM nasdaq_symbols WHERE is_active = true"
            total_count = await self.conn.fetchval(count_query)
            logger.info(f"📊 Total active symbols in database: {total_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inserting symbols: {e}")
            return False
    
    async def analyze_nasdaq_data(self):
        """Analyze the loaded NASDAQ data"""
        try:
            logger.info("📈 Analyzing NASDAQ data distribution...")
            
            # Sector distribution
            sector_query = """
                SELECT sector, COUNT(*) as count, 
                       ROUND(AVG(market_cap/1000000), 2) as avg_market_cap_millions
                FROM nasdaq_symbols 
                WHERE is_active = true AND sector != 'Unknown'
                GROUP BY sector 
                ORDER BY count DESC
            """
            
            sectors = await self.conn.fetch(sector_query)
            
            logger.info("🏢 Sector Distribution:")
            for sector in sectors[:10]:  # Top 10 sectors
                logger.info(f"   {sector['sector']}: {sector['count']} stocks (Avg Cap: ${sector['avg_market_cap_millions']}M)")
            
            # Market cap distribution
            cap_query = """
                SELECT 
                    CASE 
                        WHEN market_cap >= 200000000000 THEN 'Mega Cap (>$200B)'
                        WHEN market_cap >= 10000000000 THEN 'Large Cap ($10B-$200B)'
                        WHEN market_cap >= 2000000000 THEN 'Mid Cap ($2B-$10B)'
                        WHEN market_cap >= 300000000 THEN 'Small Cap ($300M-$2B)'
                        WHEN market_cap > 0 THEN 'Micro Cap (<$300M)'
                        ELSE 'Unknown Cap'
                    END as cap_category,
                    COUNT(*) as count
                FROM nasdaq_symbols 
                WHERE is_active = true
                GROUP BY cap_category
                ORDER BY 
                    CASE 
                        WHEN cap_category = 'Mega Cap (>$200B)' THEN 1
                        WHEN cap_category = 'Large Cap ($10B-$200B)' THEN 2
                        WHEN cap_category = 'Mid Cap ($2B-$10B)' THEN 3
                        WHEN cap_category = 'Small Cap ($300M-$2B)' THEN 4
                        WHEN cap_category = 'Micro Cap (<$300M)' THEN 5
                        ELSE 6
                    END
            """
            
            caps = await self.conn.fetch(cap_query)
            
            logger.info("💰 Market Cap Distribution:")
            for cap in caps:
                logger.info(f"   {cap['cap_category']}: {cap['count']} stocks")
            
            # Top companies by market cap
            top_companies_query = """
                SELECT symbol, name, market_cap, sector
                FROM nasdaq_symbols 
                WHERE is_active = true AND market_cap > 0
                ORDER BY market_cap DESC
                LIMIT 10
            """
            
            top_companies = await self.conn.fetch(top_companies_query)
            
            logger.info("🏆 Top 10 Companies by Market Cap:")
            for company in top_companies:
                market_cap_b = company['market_cap'] / 1_000_000_000
                logger.info(f"   {company['symbol']}: {company['name']} - ${market_cap_b:.1f}B ({company['sector']})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error analyzing data: {e}")
            return False
    
    async def prepare_surveillance_batches(self):
        """Prepare weekly surveillance batches"""
        try:
            logger.info("📅 Preparing weekly surveillance batches...")
            
            # Get all active symbols
            symbols_query = "SELECT symbol FROM nasdaq_symbols WHERE is_active = true ORDER BY symbol"
            symbols = await self.conn.fetch(symbols_query)
            symbol_list = [row['symbol'] for row in symbols]
            
            total_symbols = len(symbol_list)
            batch_size = 1000
            total_weeks = (total_symbols + batch_size - 1) // batch_size  # Ceiling division
            
            logger.info(f"📊 Total symbols: {total_symbols}")
            logger.info(f"📦 Batch size: {batch_size}")
            logger.info(f"📅 Total weeks needed: {total_weeks}")
            
            # Create batch records
            for week in range(1, total_weeks + 1):
                start_idx = (week - 1) * batch_size
                end_idx = min(start_idx + batch_size, total_symbols)
                batch_symbols = symbol_list[start_idx:end_idx]
                
                # Insert batch record
                batch_query = """
                    INSERT INTO surveillance_batches 
                    (week_number, batch_date, total_symbols, status)
                    VALUES ($1, CURRENT_DATE, $2, 'pending')
                    ON CONFLICT (week_number) DO UPDATE SET
                        total_symbols = EXCLUDED.total_symbols,
                        status = 'pending'
                """
                
                await self.conn.execute(batch_query, week, len(batch_symbols))
                
                logger.info(f"📦 Week {week}: {len(batch_symbols)} symbols ({symbol_list[start_idx]} to {symbol_list[end_idx-1]})")
            
            logger.info("✅ Surveillance batches prepared")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error preparing batches: {e}")
            return False
    
    async def run_full_setup(self):
        """Run the complete NASDAQ symbol loading process"""
        logger.info("🚀 Starting NASDAQ Surveillance System Setup")
        logger.info("=" * 60)
        
        # Connect to database
        if not await self.connect_db():
            return False
        
        try:
            # Create tables
            if not await self.create_tables():
                return False
            
            # Load CSV data
            df = self.load_nasdaq_csv()
            if df is None:
                return False
            
            # Insert symbols into database
            if not await self.insert_nasdaq_symbols(df):
                return False
            
            # Analyze the data
            if not await self.analyze_nasdaq_data():
                return False
            
            # Prepare surveillance batches
            if not await self.prepare_surveillance_batches():
                return False
            
            logger.info("=" * 60)
            logger.info("🎉 NASDAQ Surveillance System Setup Complete!")
            logger.info("✅ Database schema created")
            logger.info(f"✅ {len(df)} NASDAQ symbols loaded")
            logger.info("✅ Weekly surveillance batches prepared")
            logger.info("✅ Ready to start Week 1 surveillance")
            
            return True
            
        finally:
            await self.close_db()

async def main():
    """Main function to run the NASDAQ symbol loader"""
    loader = NASDAQSymbolLoader()
    success = await loader.run_full_setup()
    
    if success:
        print("\n🚀 Next Steps:")
        print("1. Run Week 1 surveillance: python -m scripts.run_surveillance --week 1")
        print("2. Monitor surveillance progress in surveillance_batches table")
        print("3. Check alerts in surveillance_alerts table")
        print("4. Review high-priority stocks in high_priority_stocks view")
    else:
        print("\n❌ Setup failed. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(main())
