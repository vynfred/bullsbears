# backend/app/services/catalyst_service.py
"""
Catalyst Data Service - Fetches insider trading (FMP) and economic events (FRED)
Used during prescreen and arbitrator phases to enrich stock analysis.
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# FRED Series IDs for key economic indicators
FRED_SERIES = {
    "CPI": "CPIAUCSL",      # Consumer Price Index
    "UNEMPLOYMENT": "UNRATE",  # Unemployment Rate
    "GDP": "GDP",           # Gross Domestic Product
    "FED_FUNDS": "FEDFUNDS",  # Federal Funds Rate
    "RETAIL_SALES": "RSXFS",  # Retail Sales
    "INDUSTRIAL_PROD": "INDPRO",  # Industrial Production
}

# FMP endpoints
FMP_BASE = "https://financialmodelingprep.com/api/v4"
FMP_STABLE = "https://financialmodelingprep.com/stable"


async def get_insider_trading(symbol: str, days: int = 90) -> dict:
    """
    Fetch insider trading data from FMP for a symbol.
    Returns summary: net shares, net value, buy/sell counts.
    """
    if not settings.FMP_API_KEY:
        return {"error": "FMP_API_KEY not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{FMP_BASE}/insider-trading",
                params={"symbol": symbol, "limit": 50, "apikey": settings.FMP_API_KEY}
            )
            resp.raise_for_status()
            trades = resp.json()
        
        if not trades:
            return {"has_activity": False, "net_shares": 0, "net_value": 0}
        
        # Filter to recent trades
        cutoff = datetime.now() - timedelta(days=days)
        recent_trades = []
        for t in trades:
            try:
                trade_date = datetime.strptime(t.get("transactionDate", ""), "%Y-%m-%d")
                if trade_date >= cutoff:
                    recent_trades.append(t)
            except (ValueError, TypeError):
                continue
        
        if not recent_trades:
            return {"has_activity": False, "net_shares": 0, "net_value": 0}
        
        # Calculate summary
        buy_shares = sum(t.get("securitiesTransacted", 0) for t in recent_trades 
                        if t.get("transactionType") in ["P-Purchase", "A-Award"])
        sell_shares = sum(t.get("securitiesTransacted", 0) for t in recent_trades 
                         if t.get("transactionType") in ["S-Sale", "S-Sale+OE"])
        buy_count = sum(1 for t in recent_trades if t.get("transactionType") in ["P-Purchase", "A-Award"])
        sell_count = sum(1 for t in recent_trades if t.get("transactionType") in ["S-Sale", "S-Sale+OE"])
        
        # Calculate net value
        net_value = sum(
            t.get("securitiesTransacted", 0) * t.get("price", 0) * 
            (1 if t.get("transactionType") in ["P-Purchase", "A-Award"] else -1)
            for t in recent_trades
        )
        
        return {
            "has_activity": True,
            "net_shares": buy_shares - sell_shares,
            "net_value": round(net_value, 2),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "last_filing_date": recent_trades[0].get("transactionDate") if recent_trades else None,
            "notable_insiders": list(set(t.get("reportingName", "") for t in recent_trades[:5]))
        }
        
    except Exception as e:
        logger.warning(f"Insider trading fetch failed for {symbol}: {e}")
        return {"error": str(e), "has_activity": False}


async def get_economic_events(days_ahead: int = 14) -> list[dict]:
    """
    Fetch upcoming economic events from FRED release calendar.
    Returns list of events with dates and expected impact.
    """
    if not settings.FRED_API_KEY:
        return [{"error": "FRED_API_KEY not configured"}]
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Get release dates for next 2 weeks
            today = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            
            resp = await client.get(
                "https://api.stlouisfed.org/fred/releases/dates",
                params={
                    "api_key": settings.FRED_API_KEY,
                    "file_type": "json",
                    "realtime_start": today,
                    "realtime_end": end_date,
                    "include_release_dates_with_no_data": "false"
                }
            )
            resp.raise_for_status()
            data = resp.json()
        
        events = []
        release_dates = data.get("release_dates", [])
        
        # Map to high-impact events
        high_impact = ["Employment", "CPI", "GDP", "FOMC", "Retail", "Industrial", "Housing"]
        
        for rd in release_dates[:20]:  # Limit to 20 events
            release_name = rd.get("release_name", "")
            is_high_impact = any(hi.lower() in release_name.lower() for hi in high_impact)
            
            events.append({
                "event": release_name,
                "date": rd.get("date"),
                "release_id": rd.get("release_id"),
                "impact": "HIGH" if is_high_impact else "MEDIUM"
            })
        
        return events
        
    except Exception as e:
        logger.warning(f"FRED events fetch failed: {e}")
        return [{"error": str(e)}]

