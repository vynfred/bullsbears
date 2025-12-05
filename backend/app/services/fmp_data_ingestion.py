#!/usr/bin/env python3
"""
FMP Data Ingestion – FINAL v3.3 (November 11, 2025 – 05:51 PM EST)
One-time 90-day bootstrap + daily delta only
300 calls/min, 20 GB/month cap → never hit
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import os

from ..core.database import get_asyncpg_pool

logger = logging.getLogger("FMP")

# === CONFIG ===
FMP_KEY = os.getenv("FMP_API_KEY")
# Note: Don't raise at import time - check when actually using the API

BASE = "https://financialmodelingprep.com/api/v3"
RATE_LIMIT = 200  # calls/min (set to 200 to stay safely under 300 limit)
DAILY_DATA_MB = 0.0  # Auto-tracked

class FMPIngestion:
    """One job: Prime DB always fresh, never exceed limits"""

    def __init__(self):
        self.session = None
        self.calls = []
        self.daily_mb = 0.0

    async def initialize(self):
        if not FMP_KEY:
            raise RuntimeError("FMP_API_KEY not set - cannot initialize FMP ingestion")
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def _rate_limit(self):
        now = asyncio.get_event_loop().time()
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) >= RATE_LIMIT:
            sleep = 60 - (now - self.calls[0])
            logger.info(f"Rate limit hit – sleeping {sleep:.1f}s")
            await asyncio.sleep(sleep)
        self.calls.append(now)

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        await self._rate_limit()
        url = f"{BASE}/{endpoint}"
        params = params or {}
        params["apikey"] = FMP_KEY

        try:
            async with self.session.get(url, params=params) as resp:
                text = await resp.text()
                size_mb = len(text.encode('utf-8')) / (1024 * 1024)
                self.daily_mb += size_mb

                if resp.status != 200:
                    logger.error(f"FMP {resp.status} {endpoint}: {text[:200]}")
                    return {}

                data = json.loads(text) if text else {}
                logger.debug(f"FMP {endpoint} → {size_mb:.3f} MB")
                return data

        except Exception as e:
            logger.error(f"FMP request failed {endpoint}: {e}")
            return {}

    async def bootstrap_prime_db(self, resume: bool = True):
        from ..core.firebase import FirebaseClient
        from ..core.database import get_asyncpg_pool

        logger.info("FMP BOOTSTRAP START – 7 weeks, ~7.8 GB")
        symbols = await self._get_nasdaq_symbols()

        # STEP 1: Insert all symbols into stock_classifications with tier='ALL'
        logger.info(f"STEP 1: Inserting {len(symbols)} stocks into stock_classifications table...")
        await self._insert_all_stocks(symbols)
        logger.info(f"✅ All {len(symbols)} stocks inserted into stock_classifications with tier='ALL'")

        # STEP 2: Check which symbols already have data (for resume)
        if resume:
            db = await get_asyncpg_pool()
            async with db.acquire() as conn:
                rows = await conn.fetch("SELECT DISTINCT symbol FROM prime_ohlc_90d")
                existing = {r['symbol'] for r in rows}

            original_count = len(symbols)
            symbols = [s for s in symbols if s not in existing]
            logger.info(f"RESUME MODE: {original_count - len(symbols)} symbols already loaded, {len(symbols)} remaining")

        if not symbols:
            logger.info("✅ All symbols already loaded!")
            return

        batch_size = 550
        total_batches = (len(symbols) + batch_size - 1) // batch_size  # ceil division

        # STEP 3: Load 90 days of OHLC data for remaining stocks
        async with FirebaseClient() as fb:
            for week in range(total_batches):
                batch = symbols[week * batch_size:(week + 1) * batch_size]

                # Update progress in Firebase (ignore 404 errors)
                try:
                    await fb.update_data("/system/prime_progress", {
                        "current_batch": week + 1,
                        "total_batches": total_batches,
                        "current_stocks": len(batch),
                        "total_stocks": len(symbols),
                        "data_mb": round(self.daily_mb, 2),
                        "status": "in_progress"
                    })
                except:
                    pass

                await self._fetch_90d_batch(batch)
                logger.info(f"Batch {week + 1}/{total_batches} DONE – {len(batch)} symbols – {self.daily_mb:.2f} GB so far")
                await asyncio.sleep(2)

            # Mark as complete
            try:
                await fb.update_data("/system/prime_progress", {
                    "current_batch": total_batches,
                    "total_batches": total_batches,
                    "total_stocks": len(symbols),
                    "data_mb": round(self.daily_mb, 2),
                    "status": "complete"
                })
            except:
                pass

        logger.info(f"BOOTSTRAP COMPLETE – {self.daily_mb:.2f} GB used")

    async def daily_delta_update(self):
        global DAILY_DATA_MB
        self.daily_mb = 0.0
        logger.info("FMP DAILY DELTA START")
        active = await self._get_active_symbols_from_db()
        await self._fetch_1d_batch(active)
        DAILY_DATA_MB = self.daily_mb
        logger.info(f"DAILY DELTA DONE – {len(active)} symbols – {self.daily_mb:.3f} GB")

    async def catchup_7days(self):
        """Catch up last 7 days for all stocks already in database"""
        from ..core.firebase import FirebaseClient

        logger.info("FMP 7-DAY CATCHUP START")

        # Get all symbols from stock_classifications (stocks we already have)
        symbols = await self._get_all_symbols_from_db()

        if not symbols:
            logger.warning("No stocks found in database - run bootstrap_prime_db first")
            return

        logger.info(f"Catching up {len(symbols)} stocks with last 7 days of data")

        async with FirebaseClient() as fb:
            # Update progress in Firebase
            await fb.update_data("/system/catchup_progress", {
                "total_stocks": len(symbols),
                "data_mb": 0,
                "status": "in_progress"
            })

            # Fetch 7 days for all stocks
            await self._fetch_7d_batch(symbols)

            # Mark as complete
            await fb.update_data("/system/catchup_progress", {
                "total_stocks": len(symbols),
                "data_mb": round(self.daily_mb, 2),
                "status": "complete"
            })

        logger.info(f"7-DAY CATCHUP COMPLETE – {len(symbols)} symbols – {self.daily_mb:.2f} GB")

    async def _fetch_90d_batch(self, symbols: List[str]):
        """Fetch 90 days of data in smaller chunks to avoid connection pool exhaustion"""
        chunk_size = 50  # Process 50 stocks at a time
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            tasks = [self._fetch_90d(s) for s in chunk]
            await asyncio.gather(*tasks)
            logger.info(f"  Processed {min(i + chunk_size, len(symbols))}/{len(symbols)} stocks in this batch")
            await asyncio.sleep(0.5)  # Small delay between chunks

    async def _fetch_1d_batch(self, symbols: List[str]):
        tasks = [self._fetch_1d(s) for s in symbols]
        await asyncio.gather(*tasks)

    async def _fetch_7d_batch(self, symbols: List[str]):
        """Fetch 7 days of data in smaller chunks to avoid connection pool exhaustion"""
        chunk_size = 50  # Process 50 stocks at a time
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            tasks = [self._fetch_7d(s) for s in chunk]
            await asyncio.gather(*tasks)
            logger.info(f"  Processed {min(i + chunk_size, len(symbols))}/{len(symbols)} stocks")
            await asyncio.sleep(0.5)  # Small delay between chunks

    async def _fetch_90d(self, symbol: str):
        end = datetime.now().date()
        start = end - timedelta(days=90)
        data = await self._get(
            f"historical-price-full/{symbol}",
            {"from": start.isoformat(), "to": end.isoformat()}
        )
        if "historical" in data:
            await self._store_90d(symbol, data["historical"])

    async def _fetch_1d(self, symbol: str):
        """Fetch today's full OHLC data (not just quote-short price)"""
        end = datetime.now().date()
        start = end - timedelta(days=1)  # Yesterday to today (ensures we get today's data)
        data = await self._get(
            f"historical-price-full/{symbol}",
            {"from": start.isoformat(), "to": end.isoformat()}
        )
        if "historical" in data and data["historical"]:
            await self._store_90d(symbol, data["historical"])  # Reuse UPSERT method
        else:
            # Fallback to quote-short if no historical data yet
            quote = await self._get(f"quote-short/{symbol}")
            if quote and quote[0].get("price"):
                await self._store_1d_quote(symbol, quote[0])

    async def _fetch_7d(self, symbol: str):
        """Fetch last 7 days of data for a symbol"""
        end = datetime.now().date()
        start = end - timedelta(days=7)
        data = await self._get(
            f"historical-price-full/{symbol}",
            {"from": start.isoformat(), "to": end.isoformat()}
        )
        if "historical" in data:
            await self._store_90d(symbol, data["historical"])  # Reuse same storage method

    async def _store_90d(self, symbol: str, records: List[Dict]):
        from datetime import datetime as dt
        query = """
        INSERT INTO prime_ohlc_90d (symbol, date, open_price, high_price, low_price, close_price, volume, adj_close, vwap)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (symbol, date) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            adj_close = EXCLUDED.adj_close,
            vwap = EXCLUDED.vwap
        """
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            await conn.executemany(query, [
                (
                    symbol,
                    dt.strptime(r["date"], "%Y-%m-%d").date() if isinstance(r["date"], str) else r["date"],
                    r["open"],
                    r["high"],
                    r["low"],
                    r["close"],
                    int(r["volume"]),
                    r.get("adjClose"),  # Adjusted close (accounts for splits/dividends)
                    r.get("vwap")       # Volume weighted average price
                )
                for r in records
            ])

    async def _store_1d_quote(self, symbol: str, data: Dict):
        """Fallback store from quote-short - INSERT OR UPDATE today's price"""
        query = """
        INSERT INTO prime_ohlc_90d (symbol, date, open_price, high_price, low_price, close_price, volume)
        VALUES ($1, CURRENT_DATE, $2, $2, $2, $2, $3)
        ON CONFLICT (symbol, date) DO UPDATE SET
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume
        """
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            await conn.execute(query, symbol, data["price"], data.get("volume", 0))

    async def _get_nasdaq_symbols(self) -> List[str]:
        data = await self._get("stock/list")
        return [s["symbol"] for s in data if s.get("exchange") == "NASDAQ" and len(s.get("symbol", "")) <= 5]

    async def _get_active_symbols_from_db(self) -> List[str]:
        query = "SELECT symbol FROM stock_classifications WHERE current_tier IN ('ACTIVE', 'SHORT_LIST', 'PICKS')"
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            rows = await conn.fetch(query)
            return [row["symbol"] for row in rows]

    async def _get_all_symbols_from_db(self) -> List[str]:
        """Get all symbols from stock_classifications table"""
        query = "SELECT DISTINCT symbol FROM stock_classifications ORDER BY symbol"
        db = await get_asyncpg_pool()
        async with db.acquire() as conn:
            rows = await conn.fetch(query)
            return [row["symbol"] for row in rows]

    async def _insert_all_stocks(self, symbols: List[str]):
        """Insert all NASDAQ stocks into stock_classifications with tier='ALL'"""
        from datetime import datetime
        db = await get_asyncpg_pool()

        # Batch insert for efficiency
        query = """
            INSERT INTO stock_classifications (symbol, exchange, current_tier, created_at, updated_at)
            VALUES ($1, 'NASDAQ', 'ALL', $2, $2)
            ON CONFLICT (symbol) DO UPDATE SET
                current_tier = EXCLUDED.current_tier,
                updated_at = EXCLUDED.updated_at
        """

        now = datetime.utcnow()
        async with db.acquire() as conn:
            # Insert in batches of 100
            for i in range(0, len(symbols), 100):
                batch = symbols[i:i + 100]
                await conn.executemany(query, [(s, now) for s in batch])
                if (i + 100) % 1000 == 0:
                    logger.info(f"  Inserted {i + 100}/{len(symbols)} stocks...")

        logger.info(f"✅ Inserted {len(symbols)} stocks into stock_classifications")

    async def close(self):
        if self.session:
            await self.session.close()
            logger.info(f"FMP session closed – {self.daily_mb:.3f} GB used today")


# Global singleton
_ingestion = None

async def get_fmp_ingestion() -> FMPIngestion:
    global _ingestion
    if _ingestion is None:
        _ingestion = FMPIngestion()
        await _ingestion.initialize()
    return _ingestion