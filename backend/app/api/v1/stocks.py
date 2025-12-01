from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging
import httpx
from app.services.system_state import is_system_on
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/quotes")
async def get_quotes(symbols: str = Query(..., description="Comma-separated symbols")):
    """
    Get real-time quotes from FMP for given symbols.
    Returns dict of {symbol: {price, change, changePercent}}
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

        if not symbol_list:
            return {}

        if len(symbol_list) > 50:
            raise HTTPException(400, "Maximum 50 symbols per request")

        if not settings.FMP_API_KEY:
            logger.warning("FMP_API_KEY not configured")
            return {}

        # FMP batch quote endpoint
        symbols_str = ",".join(symbol_list)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}",
                params={"apikey": settings.FMP_API_KEY}
            )

            if resp.status_code != 200:
                logger.warning(f"FMP API error: {resp.status_code}")
                return {}

            quotes = resp.json()

            # Transform to simple format
            result = {}
            for q in quotes:
                result[q["symbol"]] = {
                    "price": float(q.get("price", 0)),
                    "change": float(q.get("change", 0)),
                    "changePercent": float(q.get("changesPercentage", 0)),
                }

            return result

    except httpx.TimeoutException:
        logger.warning("FMP API timeout")
        return {}
    except Exception as e:
        logger.error(f"Quote fetch error: {e}")
        return {}


# Only keep this endpoint — it’s perfect for admin panel
@router.post("/trigger-pipeline")
async def manual_trigger_pipeline():
    if not await is_system_on():
        raise HTTPException(403, detail="System is OFF – enable in /internal/system/on")

    from app.tasks.fmp_delta_update import fmp_delta_update
    fmp_delta_update.delay()  # fire and forget
    return {"status": "Full pipeline triggered manually"}