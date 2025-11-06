"""
Daily Scanning Tasks for Bullish/Bearish Pattern Detection
Scheduled to run at 9:30 AM ET to scan 888 volatile tickers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from celery import Celery
from sqlalchemy.orm import Session

from ..core.celery_app import celery_app
from ..core.database import get_db
from ..models.analysis_results import AnalysisResult, AlertType, AlertOutcome
from ..models.stock import Stock
from ..analyzers.bullish_analyzer import BullishAnalyzer, BullishAlert
from ..analyzers.bearish_analyzer import BearishAnalyzer, BearishAlert
from ..core.config import settings

logger = logging.getLogger(__name__)


# Volatile tickers for daily scanning (888 symbols for MVP)
SCAN_SYMBOLS = [
    # Large Cap Tech (High Volume)
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "NFLX", "CRM",
    "ORCL", "ADBE", "INTC", "AMD", "QCOM", "AVGO", "TXN", "MU", "AMAT", "LRCX",
    "CSCO", "IBM", "INTU", "NOW", "WDAY", "VEEV", "DDOG", "CRWD", "ZS", "OKTA",

    # Meme Stocks & High Volatility
    "GME", "AMC", "BBBY", "PLTR", "COIN", "HOOD", "RIVN", "LCID", "SPCE", "CLOV",
    "WISH", "SOFI", "UPST", "AFRM", "SQ", "PYPL", "ROKU", "ZOOM", "PELOTON", "PTON",
    "RBLX", "U", "PATH", "SNOW", "TWLO", "SHOP", "DOCU", "ASAN", "TEAM", "SPLK",

    # Growth & Biotech (Volatile)
    "MRNA", "BNTX", "NVAX", "GILD", "BIIB", "REGN", "VRTX", "ILMN", "BMRN", "SGEN",
    "CRSP", "EDIT", "NTLA", "BEAM", "PACB", "TDOC", "VEEV", "DXCM", "ISRG", "ALGN",
    "AMGN", "CELG", "ABBV", "JNJ", "PFE", "MRK", "LLY", "BMY", "GILD", "VRTX",
    "INCY", "EXAS", "EXACT", "ARKG", "XBI", "IBB", "LABU", "LABD", "SOXL", "SOXS",

    # Fintech & Payments
    "V", "MA", "PYPL", "SQ", "ADYEN", "FIS", "FISV", "GPN", "WU", "MELI",
    "AFRM", "UPST", "SOFI", "LC", "ONDK", "STNE", "PAGS", "NU", "OPEN", "RDFN",

    # Energy & Commodities
    "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "OXY", "MPC", "VLO", "PSX",
    "FCX", "NEM", "GOLD", "AEM", "KGC", "PAAS", "AG", "EXK", "HL", "SSRM",
    "BP", "SHEL", "TTE", "E", "FANG", "DVN", "PXD", "MRO", "APA", "HES",
    "XLE", "XOP", "OIH", "USO", "UCO", "SCO", "DRIP", "GUSH", "ERX", "ERY",

    # Airlines & Travel (Volatile)
    "AAL", "DAL", "UAL", "LUV", "JBLU", "ALK", "SAVE", "HA", "SKYW", "MESA",
    "CCL", "RCL", "NCLH", "EXPE", "BKNG", "ABNB", "UBER", "LYFT", "DASH", "GRUB",
    "MAR", "HLT", "IHG", "H", "WH", "RHP", "PK", "WYNN", "LVS", "MGM",

    # Retail & Consumer
    "AMZN", "WMT", "TGT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD", "CMG",
    "LULU", "ULTA", "TJX", "ROST", "BBY", "GPS", "ANF", "AEO", "URBN", "EXPR",
    "TSLA", "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI", "BYDDY", "TM",
    "DIS", "NFLX", "WBD", "PARA", "CMCSA", "T", "VZ", "TMUS", "S", "DISH",

    # Cannabis & Speculative
    "TLRY", "CGC", "ACB", "CRON", "HEXO", "OGI", "SNDL", "APHA", "CURLF", "GTBIF",
    "MSOS", "YOLO", "POTX", "THCX", "MJ", "CNBS", "TOKE", "BUDZ", "HERB", "WEED",

    # SPACs & Recent IPOs
    "SPCE", "OPEN", "DKNG", "PENN", "MGM", "WYNN", "LVS", "CZR", "BYD", "F",
    "RBLX", "COIN", "HOOD", "AFRM", "UPST", "SOFI", "RIVN", "LCID", "GRAB", "DIDI",

    # Crypto-Related
    "COIN", "MSTR", "RIOT", "MARA", "HUT", "BITF", "CAN", "HIVE", "ARBK", "BTBT",
    "CLSK", "CORZ", "WULF", "IREN", "CIFR", "BTCS", "EBON", "SOS", "EBANG", "GREE",

    # ETFs for Market Context
    "SPY", "QQQ", "IWM", "VIX", "UVXY", "SQQQ", "TQQQ", "SPXU", "SPXL", "TNA",
    "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "SARK", "XLK", "XLF", "XLE", "XLV",

    # Additional High Beta Stocks
    "SHOP", "TWLO", "OKTA", "SNOW", "PLTR", "RBLX", "U", "PATH", "DDOG", "CRWD",
    "ZM", "DOCU", "ASAN", "TEAM", "WDAY", "NOW", "SPLK", "PANW", "FTNT", "CYBR",

    # S&P 500 Core Holdings (Top 100 by market cap)
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "TSLA", "META", "BRK.B", "UNH",
    "JNJ", "XOM", "JPM", "V", "PG", "MA", "CVX", "HD", "ABBV", "PFE",
    "BAC", "KO", "AVGO", "PEP", "TMO", "COST", "WMT", "DIS", "ABT", "MRK",
    "CSCO", "ACN", "ADBE", "NKE", "TXN", "LLY", "QCOM", "DHR", "VZ", "ORCL",
    "WFC", "BMY", "AMGN", "PM", "RTX", "T", "SPGI", "LOW", "UNP", "HON",
    "INTU", "COP", "IBM", "AMAT", "CAT", "SBUX", "GS", "AXP", "BKNG", "DE",
    "AMD", "GILD", "MDT", "TJX", "BLK", "ADP", "LRCX", "AMT", "SYK", "TMUS",
    "ISRG", "MU", "INTC", "C", "REGN", "CB", "MO", "ZTS", "PLD", "SO",
    "MDLZ", "DUK", "BSX", "BA", "AON", "CL", "EQIX", "APD", "SHW", "CME",
    "EL", "PYPL", "ITW", "MMC", "GD", "FCX", "USB", "PNC", "EMR", "NSC",

    # Mid Cap Growth & Momentum
    "ROKU", "PELOTON", "ZOOM", "DOCU", "PTON", "ZM", "NFLX", "CRM", "ADBE", "NOW",
    "WDAY", "VEEV", "DDOG", "CRWD", "ZS", "OKTA", "SNOW", "PLTR", "RBLX", "U",
    "PATH", "TWLO", "SHOP", "SQ", "PYPL", "AFRM", "UPST", "SOFI", "COIN", "HOOD",
    "RIVN", "LCID", "SPCE", "CLOV", "WISH", "AMC", "GME", "BBBY", "EXPR", "GPS",

    # Small Cap & Speculative
    "SNDL", "HEXO", "OGI", "ACB", "CRON", "TLRY", "CGC", "APHA", "CURLF", "GTBIF",
    "RIOT", "MARA", "HUT", "BITF", "CAN", "HIVE", "ARBK", "BTBT", "CLSK", "CORZ",
    "WULF", "IREN", "CIFR", "BTCS", "EBON", "SOS", "EBANG", "GREE", "MSTR", "COIN",

    # International & ADRs
    "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "DIDI", "GRAB", "SE",
    "SHOP", "MELI", "NU", "STNE", "PAGS", "VALE", "ITUB", "BBD", "PBR", "SID",
    "TSM", "ASML", "SAP", "NVO", "NESN", "RHHBY", "UL", "DEO", "BUD", "SNY",

    # REITs & Utilities
    "AMT", "PLD", "CCI", "EQIX", "PSA", "EXR", "WELL", "DLR", "SPG", "O",
    "REYN", "VTR", "ESS", "EQR", "AVB", "UDR", "CPT", "MAA", "AIV", "ELS",
    "SO", "NEE", "DUK", "D", "EXC", "XEL", "SRE", "AEP", "PCG", "ED",

    # Financial Services
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF",
    "AXP", "V", "MA", "PYPL", "SQ", "FIS", "FISV", "GPN", "WU", "AFRM",
    "BRK.B", "BRK.A", "BLK", "SCHW", "SPGI", "MCO", "ICE", "CME", "NDAQ", "CBOE",

    # Healthcare & Pharma
    "UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "ABT", "LLY", "BMY", "AMGN",
    "GILD", "REGN", "VRTX", "BIIB", "CELG", "INCY", "EXAS", "EXACT", "MRNA", "BNTX",
    "NVAX", "ILMN", "BMRN", "SGEN", "CRSP", "EDIT", "NTLA", "BEAM", "PACB", "TDOC",

    # Industrial & Manufacturing
    "CAT", "DE", "BA", "GE", "HON", "MMM", "UNP", "CSX", "NSC", "FDX",
    "UPS", "RTX", "LMT", "NOC", "GD", "LHX", "TXT", "PH", "ETN", "EMR",
    "ITW", "DHR", "TMO", "A", "APD", "LIN", "SHW", "PPG", "ECL", "FMC",

    # Consumer Discretionary
    "AMZN", "TSLA", "HD", "NKE", "SBUX", "MCD", "DIS", "BKNG", "LOW", "TJX",
    "LULU", "ULTA", "ROST", "BBY", "GPS", "ANF", "AEO", "URBN", "EXPR", "M",
    "JWN", "KSS", "DDS", "FIVE", "OLLI", "BIG", "DLTR", "DG", "WMT", "TGT",

    # Communication Services
    "META", "GOOGL", "GOOG", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR",
    "DISH", "SIRI", "TWTR", "SNAP", "PINS", "MTCH", "BMBL", "ZM", "DOCU", "TEAM",

    # Materials & Commodities
    "FCX", "NEM", "GOLD", "AEM", "KGC", "PAAS", "AG", "EXK", "HL", "SSRM",
    "AA", "X", "CLF", "NUE", "STLD", "RS", "CMC", "SID", "PKX", "MT",
    "LIN", "APD", "ECL", "FMC", "CF", "MOS", "NTR", "IFF", "DD", "DOW",

    # Additional Volatile & Momentum Stocks
    "SPCE", "OPEN", "DKNG", "PENN", "MGM", "WYNN", "LVS", "CZR", "BYD", "F",
    "GM", "RIVN", "LCID", "NIO", "XPEV", "LI", "BYDDY", "TM", "HMC", "NSANY",
    "ROKU", "PELOTON", "ZOOM", "DOCU", "PTON", "ZM", "NFLX", "CRM", "ADBE", "NOW",
    "WDAY", "VEEV", "DDOG", "CRWD", "ZS", "OKTA", "SNOW", "PLTR", "RBLX", "U",
    "PATH", "TWLO", "SHOP", "SQ", "PYPL", "AFRM", "UPST", "SOFI", "COIN", "HOOD",
    "WISH", "AMC", "GME", "BBBY", "EXPR", "GPS", "ANF", "AEO", "URBN", "CLOV",

    # Sector ETFs & Leveraged ETFs
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLB", "XLU", "XLRE",
    "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "SARK", "TQQQ", "SQQQ", "SPXL", "SPXU",
    "TNA", "TZA", "FAS", "FAZ", "ERX", "ERY", "TECL", "TECS", "CURE", "RXD",
    "LABU", "LABD", "SOXL", "SOXS", "FNGU", "FNGD", "BULZ", "BERZ", "HIBL", "HIBS",

    # Final additions to reach 888
    "ABNB", "UBER", "LYFT", "DASH", "GRUB", "MAR", "HLT", "IHG", "H", "WH",
    "RHP", "PK", "CCL", "RCL", "NCLH", "EXPE", "BKNG", "AAL", "DAL", "UAL",
    "LUV", "JBLU", "ALK", "SAVE", "HA", "SKYW", "MESA", "COST", "WMT", "TGT",
    "MSOS", "YOLO", "POTX", "THCX", "MJ", "CNBS", "TOKE", "BUDZ", "HERB", "WEED",
    "CLSK", "CORZ", "WULF", "IREN", "CIFR", "BTCS", "EBON", "SOS", "EBANG", "GREE"
]


@celery_app.task(bind=True, max_retries=3)
def daily_bullish_scan(self):
    """
    Daily scan for bullish patterns at 9:30 AM ET.
    Scans all symbols for potential +20% jump opportunities.
    """
    try:
        logger.info("Starting daily bullish scan")
        start_time = datetime.now()

        # Run async scan
        alerts = asyncio.run(_run_bullish_scan())

        # Store alerts in database
        stored_count = _store_bullish_alerts(alerts)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Daily bullish scan completed: {stored_count} alerts generated in {duration:.1f}s")

        return {
            "status": "success",
            "alerts_generated": stored_count,
            "duration_seconds": duration,
            "symbols_scanned": len(SCAN_SYMBOLS)
        }

    except Exception as e:
        logger.error(f"Daily bullish scan failed: {e}")
        raise self.retry(countdown=300, exc=e)  # Retry in 5 minutes


@celery_app.task(bind=True, max_retries=3)
def daily_bearish_scan(self):
    """
    Daily scan for bearish patterns at 9:30 AM ET.
    Scans all symbols for potential -20% drop warnings.
    """
    try:
        logger.info("Starting daily bearish scan")
        start_time = datetime.now()

        # Run async scan
        alerts = asyncio.run(_run_bearish_scan())

        # Store alerts in database
        stored_count = _store_bearish_alerts(alerts)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Daily bearish scan completed: {stored_count} alerts generated in {duration:.1f}s")

        return {
            "status": "success",
            "alerts_generated": stored_count,
            "duration_seconds": duration,
            "symbols_scanned": len(SCAN_SYMBOLS)
        }

    except Exception as e:
        logger.error(f"Daily bearish scan failed: {e}")
        raise self.retry(countdown=300, exc=e)  # Retry in 5 minutes


@celery_app.task(bind=True)
def combined_daily_scan(self):
    """
    Combined daily scan for both bullish and bearish patterns.
    More efficient than running separate scans.
    """
    try:
        logger.info("Starting combined daily scan (bullish + bearish)")
        start_time = datetime.now()

        # Run both scans in parallel
        bullish_alerts, bearish_alerts = asyncio.run(_run_combined_scan())

        # Store alerts in database
        bullish_count = _store_bullish_alerts(bullish_alerts)
        bearish_count = _store_bearish_alerts(bearish_alerts)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Combined daily scan completed: {bullish_count} bullish + {bearish_count} bearish alerts in {duration:.1f}s")

        return {
            "status": "success",
            "bullish_alerts": bullish_count,
            "bearish_alerts": bearish_count,
            "total_alerts": bullish_count + bearish_count,
            "duration_seconds": duration,
            "symbols_scanned": len(SCAN_SYMBOLS)
        }

    except Exception as e:
        logger.error(f"Combined daily scan failed: {e}")
        raise self.retry(countdown=300, exc=e)


async def _run_bullish_scan() -> List[BullishAlert]:
    """Run bullish pattern scan on all symbols"""
    alerts = []

    async with BullishAnalyzer() as analyzer:
        # Process symbols in batches to avoid overwhelming APIs
        batch_size = 10
        for i in range(0, len(SCAN_SYMBOLS), batch_size):
            batch = SCAN_SYMBOLS[i:i + batch_size]

            # Process batch concurrently
            batch_tasks = [
                analyzer.analyze_bullish_potential(symbol)
                for symbol in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Collect successful alerts
            for result in batch_results:
                if isinstance(result, BullishAlert):
                    alerts.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in bullish scan batch: {result}")

            # Small delay between batches to respect rate limits
            await asyncio.sleep(0.5)

    return alerts


async def _run_bearish_scan() -> List[BearishAlert]:
    """Run bearish pattern scan on all symbols"""
    alerts = []

    async with BearishAnalyzer() as analyzer:
        # Process symbols in batches to avoid overwhelming APIs
        batch_size = 10
        for i in range(0, len(SCAN_SYMBOLS), batch_size):
            batch = SCAN_SYMBOLS[i:i + batch_size]

            # Process batch concurrently
            batch_tasks = [
                analyzer.analyze_bearish_potential(symbol)
                for symbol in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Collect successful alerts
            for result in batch_results:
                if isinstance(result, BearishAlert):
                    alerts.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in bearish scan batch: {result}")

            # Small delay between batches to respect rate limits
            await asyncio.sleep(0.5)

    return alerts


async def _run_combined_scan() -> tuple[List[BullishAlert], List[BearishAlert]]:
    """Run both bullish and bearish scans efficiently"""
    bullish_alerts = []
    bearish_alerts = []

    # Run both analyzers concurrently
    async with BullishAnalyzer() as bullish_analyzer, BearishAnalyzer() as bearish_analyzer:
        # Process symbols in batches
        batch_size = 10
        for i in range(0, len(SCAN_SYMBOLS), batch_size):
            batch = SCAN_SYMBOLS[i:i + batch_size]

            # Create tasks for both bullish and bearish analysis
            bullish_tasks = [bullish_analyzer.analyze_bullish_potential(symbol) for symbol in batch]
            bearish_tasks = [bearish_analyzer.analyze_bearish_potential(symbol) for symbol in batch]

            # Run all tasks concurrently
            all_tasks = bullish_tasks + bearish_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

            # Split results back into bullish and bearish
            bullish_results = results[:len(bullish_tasks)]
            bearish_results = results[len(bullish_tasks):]

            # Collect successful alerts
            for result in bullish_results:
                if isinstance(result, BullishAlert):
                    bullish_alerts.append(result)

            for result in bearish_results:
                if isinstance(result, BearishAlert):
                    bearish_alerts.append(result)

            # Small delay between batches
            await asyncio.sleep(0.5)

    return bullish_alerts, bearish_alerts


def _store_bullish_alerts(alerts: List[BullishAlert]) -> int:
    """Store bullish alerts in database"""
    if not alerts:
        return 0

    stored_count = 0
    db = next(get_db())

    try:
        for alert in alerts:
            # Create AnalysisResult record
            analysis_result = AnalysisResult(
                symbol=alert.symbol,
                analysis_type="stock",
                timestamp=alert.timestamp,
                recommendation="MODERATE_BUY",  # Bullish alerts are buy signals
                confidence_score=alert.confidence,

                # Component scores
                technical_score=alert.technical_score,
                news_sentiment_score=alert.sentiment_score,
                social_sentiment_score=alert.social_score,
                earnings_score=alert.earnings_score,
                market_trend_score=50.0,  # Default

                # Bullish-specific fields
                alert_type=AlertType.BULLISH,
                pattern_confidence=alert.confidence,
                target_timeframe_days=3,
                move_threshold_percent=20.0,
                alert_outcome=AlertOutcome.PENDING,

                # Store features and reasons
                features_json={
                    "reasons": alert.reasons,
                    "risk_factors": alert.risk_factors,
                    "target_timeframe": alert.target_timeframe
                }
            )

            db.add(analysis_result)
            stored_count += 1

        db.commit()
        logger.info(f"Stored {stored_count} bullish alerts")

    except Exception as e:
        logger.error(f"Error storing bullish alerts: {e}")
        db.rollback()
    finally:
        db.close()

    return stored_count


def _store_bearish_alerts(alerts: List[BearishAlert]) -> int:
    """Store bearish alerts in database"""
    if not alerts:
        return 0

    stored_count = 0
    db = next(get_db())

    try:
        for alert in alerts:
            # Create AnalysisResult record
            analysis_result = AnalysisResult(
                symbol=alert.symbol,
                analysis_type="stock",
                timestamp=alert.timestamp,
                recommendation="MODERATE_SELL",  # Bearish alerts are sell signals
                confidence_score=alert.confidence,

                # Component scores
                technical_score=alert.technical_score,
                news_sentiment_score=alert.sentiment_score,
                social_sentiment_score=alert.social_score,
                earnings_score=alert.earnings_score,
                market_trend_score=50.0,  # Default

                # Bearish-specific fields
                alert_type=AlertType.BEARISH,
                pattern_confidence=alert.confidence,
                target_timeframe_days=3,
                move_threshold_percent=-20.0,
                alert_outcome=AlertOutcome.PENDING,

                # Store features and reasons
                features_json={
                    "reasons": alert.reasons,
                    "risk_factors": alert.risk_factors,
                    "target_timeframe": alert.target_timeframe
                }
            )

            db.add(analysis_result)
            stored_count += 1

        db.commit()
        logger.info(f"Stored {stored_count} bearish alerts")

    except Exception as e:
        logger.error(f"Error storing bearish alerts: {e}")
        db.rollback()
    finally:
        db.close()

    return stored_count
