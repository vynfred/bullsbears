#!/usr/bin/env python3
"""
Standalone bootstrap script for BullsBears database
Can be run directly on Render as a one-off job or cron
Usage: python -m scripts.bootstrap_db
"""

import asyncio
import os
import sys

# Add parent to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run_bootstrap():
    """Run the full 90-day bootstrap"""
    print("=" * 60)
    print("BullsBears Database Bootstrap")
    print("=" * 60)
    
    # Check env vars
    fmp_key = os.getenv("FMP_API_KEY")
    db_url = os.getenv("DATABASE_URL")
    
    if not fmp_key:
        print("ERROR: FMP_API_KEY not set")
        return False
    
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return False
    
    print(f"✓ FMP_API_KEY: {fmp_key[:8]}...")
    print(f"✓ DATABASE_URL: {db_url[:30]}...")
    
    try:
        from app.services.fmp_data_ingestion import get_fmp_ingestion
        
        print("\n[1/2] Initializing FMP client...")
        ingestion = await get_fmp_ingestion()
        
        print("[2/2] Starting 90-day bootstrap (this takes ~25 min)...")
        await ingestion.bootstrap_prime_db()
        
        print("\n" + "=" * 60)
        print(f"✅ BOOTSTRAP COMPLETE - {ingestion.daily_mb:.2f} MB downloaded")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ BOOTSTRAP FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_catchup():
    """Run 7-day catchup for existing stocks"""
    print("=" * 60)
    print("BullsBears 7-Day Catchup")
    print("=" * 60)
    
    try:
        from app.services.fmp_data_ingestion import get_fmp_ingestion
        
        print("Initializing FMP client...")
        ingestion = await get_fmp_ingestion()
        
        print("Starting 7-day catchup...")
        await ingestion.catchup_7days()
        
        print(f"\n✅ CATCHUP COMPLETE - {ingestion.daily_mb:.2f} MB downloaded")
        return True
        
    except Exception as e:
        print(f"\n❌ CATCHUP FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "bootstrap"
    
    if mode == "catchup":
        success = asyncio.run(run_catchup())
    else:
        success = asyncio.run(run_bootstrap())
    
    sys.exit(0 if success else 1)

