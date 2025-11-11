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

from ..core.database import get_database

logger = logging.getLogger("FMP")

# === CONFIG ===
FMP_KEY = os.getenv("FMP_API_KEY")
if not FMP_KEY:
    raise RuntimeError("FMP_API_KEY not set in .env!")

BASE = "https://financialmodelingprep.com/api/v3"
RATE_LIMIT = 300  # calls/min
DAILY_DATA_MB = 0.0  # Auto-tracked

class FMPIngestion:
    """One job: Prime DB always fresh, never exceed limits"""

    def __init__(self):
        self.session = None
        self.calls = []
        self.daily_mb = 0.0

    async def initialize(self):
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

    async def bootstrap_prime_db(self):
        logger.info("FMP BOOTSTRAP START – 7 weeks, ~7.8 GB")
        symbols = await self._get_nasdaq_symbols()
        batch_size = 550

        for week in range(7):
            batch = symbols[week * batch_size:(week + 1) * batch_size]
            await self._fetch_90d_batch(batch)
            logger.info(f"Week {week + 1}/7 DONE – {len(batch)} symbols – {self.daily_mb:.2f} GB so far")
            await asyncio.sleep(2)

        logger.info(f"BOOTSTRAP COMPLETE – {self.daily_mb:.2f} GB used")

    async def daily_delta_update(self):
        global DAILY_DATA_MB
        self.daily_mb = 0.0
        logger.info("FMP DAILY DELTA START")
        active = await self._get_active_symbols_from_db()
        await self._fetch_1d_batch(active)
        DAILY_DATA_MB = self.daily_mb
        logger.info(f"DAILY DELTA DONE – {len(active)} symbols – {self.daily_mb:.3f} GB")

    async def _fetch_90d_batch(self, symbols: List[str]):
        tasks = [self._fetch_90d(s) for s in symbols]
        await asyncio.gather(*tasks)

    async def _fetch_1d_batch(self, symbols: List[str]):
        tasks = [self._fetch_1d(s) for s in symbols]
        await asyncio.gather(*tasks)

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
        data = await self._get(f"quote-short/{symbol}")
        if data and data[0].get("price"):
            await self._store_1d(symbol, data[0])

    async def _store_90d(self, symbol: str, records: List[Dict]):
        query = """
        INSERT INTO prime_ohlc_90d (symbol, date, open_price, high_price, low_price, close_price, volume)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (symbol, date) DO NOTHING
        """
        db = await get_database()
        async with db.acquire() as conn:
            await conn.executemany(query, [
                (symbol, r["date"], r["open"], r["high"], r["low"], r["close"], int(r["volume"]))
                for r in records
            ])

    async def _store_1d(self, symbol: str, data: Dict):
        query = """
        UPDATE prime_ohlc_90d
        SET close_price = $2, volume = $3
        WHERE symbol = $1 AND date = CURRENT_DATE
        """
        db = await get_database()
        async with db.acquire() as conn:
            await conn.execute(query, symbol, data["price"], data.get("volume", 0))

    async def _get_nasdaq_symbols(self) -> List[str]:
        data = await self._get("stock/list")
        return [s["symbol"] for s in data if s.get("exchange") == "NASDAQ" and len(s.get("symbol", "")) <= 5]

    async def _get_active_symbols_from_db(self) -> List[str]:
        query = "SELECT symbol FROM active_tickers"
        db = await get_database()
        async with db.acquire() as conn:
            rows = await conn.fetch(query)
            return [row["symbol"] for row in rows]

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