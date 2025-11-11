#!/usr/bin/env python3
"""
Check stock data in database
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import get_database

async def check_data():
    db = await get_database()
    
    try:
        # Check sample data
        sample = await db.fetch('SELECT symbol, price, market_cap, daily_volume FROM stock_classifications LIMIT 10')
        print("Sample stock data:")
        for row in sample:
            print(f'{row["symbol"]}: price={row["price"]}, mcap={row["market_cap"]}, vol={row["daily_volume"]}')
        
        # Check tier counts
        counts = await db.fetch('SELECT current_tier, COUNT(*) as count FROM stock_classifications GROUP BY current_tier')
        print("\nTier counts:")
        for row in counts:
            print(f'{row["current_tier"]}: {row["count"]} stocks')
            
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_data())
