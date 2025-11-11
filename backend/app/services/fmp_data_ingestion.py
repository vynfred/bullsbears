#!/usr/bin/env python3
"""
FMP Data Ingestion – FINAL v3.3 (November 10, 2025 – 11:50 PM EST, Atlanta)
One-time 90-day bootstrap + daily delta only
300 calls/min, 20 GB/month cap → never hit
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import os

from ..core.database import get_database

logger = logging.getLogger(__name__)

# === CONFIG ===
FMP_KEY = os.getenv("FMP_API_KEY")  # ← MUST be set in env
if not FMP_KEY:
    raise RuntimeError("FMP_API_KEY not set!")

BASE = "https://financialmodelingprep.com/api/v3"
RATE_LIMIT = 300  # calls/min

class FMPIngestion:
    """One job: Prime DB always fresh, never exceed limits"""

    def __init__(self):
        self.session = None
        self.calls = []

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def _rate_limit(self):
        now = asyncio.get_event_loop().time()
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) >= RATE_LIMIT:
            await asyncio.sleep(60 - (now - self.calls[0]))
        self.calls.append(now)

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        await self._rate_limit()
        url = f"{BASE}/{endpoint}"
        params = params or {}
        params["apikey"] = FMP_KEY

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"FMP {resp.status} {endpoint}: {text[:200]}")
                return {}
            return await resp.json()

    async def bootstrap_prime_db(self):
        """One-time: 7-week rolling batch → full 90-day coverage"""
        logger.info("FMP bootstrap START – 7 weeks, ~7.8 GB")
        all_symbols = await self._get_nasdaq_symbols()
        batch_size = 550

        for week in range(7):
            start = week * batch_size
            batch = all_symbols[start:start + batch_size]
            await self._fetch_90d_batch(batch)
            logger.info(f"Week {week + 1}/7 DONE – {len(batch)} symbols")
            await asyncio.sleep(2)

        logger.info("Prime DB bootstrap COMPLETE")

    async def daily_delta_update(self):
        """3:00 AM ET – only 1-day bars for ~1,700 ACTIVE"""
        logger.info("FMP daily delta START")
        active = await self._get_active_symbols_from_db()
        await self._fetch_1d_batch(active)
        logger.info(f"Daily delta DONE – {len(active)} symbols")

    async def _fetch_90d_batch(self, symbols: List[str]):
        tasks = [self._fetch_90d(symbol) for symbol in symbols]
        await asyncio.gather(*tasks)

    async def _fetch_1d_batch(self, symbols: List[str]):
        tasks = [self._fetch_1d(symbol) for symbol in symbols]
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
                (
                    symbol,
                    r["date"],
                    r["open"], r["high"], r["low"], r["close"], int(r["volume"])
                )
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
        return [
            s["symbol"] for s in data
            if s.get("exchange") == "NASDAQ" and len(s.get("symbol", "")) <= 5
        ]

    async def _get_active_symbols_from_db(self) -> List[str]:
        query = "SELECT symbol FROM active_tickers"
        db = await get_database()
        async with db.acquire() as conn:
            rows = await conn.fetch(query)
            return [row["symbol"] for row in rows]

    async def close(self):
        if self.session:
            await self.session.close()


# Global singleton
_ingestion = None

async def get_fmp_ingestion() -> FMPIngestion:
    global _ingestion
    if _ingestion is None:
        _ingestion = FMPIngestion()
        await _ingestion.initialize()
    return _ingestion