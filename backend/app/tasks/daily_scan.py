"""
Daily Scanning Tasks for Moon/Rug Pattern Detection
Scheduled to run at 9:30 AM ET to scan ~200 volatile tickers
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
from ..analyzers.moon_analyzer import MoonAnalyzer, MoonAlert
from ..analyzers.rug_analyzer import RugAnalyzer, RugAlert
from ..core.config import settings

logger = logging.getLogger(__name__)


# Volatile tickers for daily scanning (200 symbols)
SCAN_SYMBOLS = [
    # Large Cap Tech (High Volume)
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "NFLX", "CRM",
    "ORCL", "ADBE", "INTC", "AMD", "QCOM", "AVGO", "TXN", "MU", "AMAT", "LRCX",
    
    # Meme Stocks & High Volatility
    "GME", "AMC", "BBBY", "PLTR", "COIN", "HOOD", "RIVN", "LCID", "SPCE", "CLOV",
    "WISH", "SOFI", "UPST", "AFRM", "SQ", "PYPL", "ROKU", "ZOOM", "PELOTON", "PTON",
    
    # Growth & Biotech (Volatile)
    "MRNA", "BNTX", "NVAX", "GILD", "BIIB", "REGN", "VRTX", "ILMN", "BMRN", "SGEN",
    "CRSP", "EDIT", "NTLA", "BEAM", "PACB", "TDOC", "VEEV", "DXCM", "ISRG", "ALGN",
    
    # Fintech & Payments
    "V", "MA", "PYPL", "SQ", "ADYEN", "FIS", "FISV", "GPN", "WU", "MELI",
    
    # Energy & Commodities
    "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "OXY", "MPC", "VLO", "PSX",
    "FCX", "NEM", "GOLD", "AEM", "KGC", "PAAS", "AG", "EXK", "HL", "SSRM",
    
    # Airlines & Travel (Volatile)
    "AAL", "DAL", "UAL", "LUV", "JBLU", "ALK", "SAVE", "HA", "SKYW", "MESA",
    "CCL", "RCL", "NCLH", "EXPE", "BKNG", "ABNB", "UBER", "LYFT", "DASH", "GRUB",
    
    # Retail & Consumer
    "AMZN", "WMT", "TGT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD", "CMG",
    "LULU", "ULTA", "TJX", "ROST", "BBY", "GPS", "ANF", "AEO", "URBN", "EXPR",
    
    # Cannabis & Speculative
    "TLRY", "CGC", "ACB", "CRON", "HEXO", "OGI", "SNDL", "APHA", "CURLF", "GTBIF",
    
    # SPACs & Recent IPOs
    "SPCE", "OPEN", "DKNG", "PENN", "MGM", "WYNN", "LVS", "CZR", "BYD", "F",
    
    # Crypto-Related
    "COIN", "MSTR", "RIOT", "MARA", "HUT", "BITF", "CAN", "HIVE", "ARBK", "BTBT",
    
    # ETFs for Market Context
    "SPY", "QQQ", "IWM", "VIX", "UVXY", "SQQQ", "TQQQ", "SPXU", "SPXL", "TNA",
    
    # Additional High Beta Stocks
    "SHOP", "TWLO", "OKTA", "SNOW", "PLTR", "RBLX", "U", "PATH", "DDOG", "CRWD",
    "ZM", "DOCU", "ASAN", "TEAM", "WDAY", "NOW", "SPLK", "PANW", "FTNT", "CYBR"
]


@celery_app.task(bind=True, max_retries=3)
def daily_moon_scan(self):
    """
    Daily scan for moon patterns at 9:30 AM ET.
    Scans all symbols for potential +20% jump opportunities.
    """
    try:
        logger.info("Starting daily moon scan")
        start_time = datetime.now()
        
        # Run async scan
        alerts = asyncio.run(_run_moon_scan())
        
        # Store alerts in database
        stored_count = _store_moon_alerts(alerts)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Daily moon scan completed: {stored_count} alerts generated in {duration:.1f}s")
        
        return {
            "status": "success",
            "alerts_generated": stored_count,
            "duration_seconds": duration,
            "symbols_scanned": len(SCAN_SYMBOLS)
        }
        
    except Exception as e:
        logger.error(f"Daily moon scan failed: {e}")
        raise self.retry(countdown=300, exc=e)  # Retry in 5 minutes


@celery_app.task(bind=True, max_retries=3)
def daily_rug_scan(self):
    """
    Daily scan for rug patterns at 9:30 AM ET.
    Scans all symbols for potential -20% drop warnings.
    """
    try:
        logger.info("Starting daily rug scan")
        start_time = datetime.now()
        
        # Run async scan
        alerts = asyncio.run(_run_rug_scan())
        
        # Store alerts in database
        stored_count = _store_rug_alerts(alerts)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Daily rug scan completed: {stored_count} alerts generated in {duration:.1f}s")
        
        return {
            "status": "success",
            "alerts_generated": stored_count,
            "duration_seconds": duration,
            "symbols_scanned": len(SCAN_SYMBOLS)
        }
        
    except Exception as e:
        logger.error(f"Daily rug scan failed: {e}")
        raise self.retry(countdown=300, exc=e)  # Retry in 5 minutes


@celery_app.task(bind=True)
def combined_daily_scan(self):
    """
    Combined daily scan for both moon and rug patterns.
    More efficient than running separate scans.
    """
    try:
        logger.info("Starting combined daily scan (moon + rug)")
        start_time = datetime.now()
        
        # Run both scans in parallel
        moon_alerts, rug_alerts = asyncio.run(_run_combined_scan())
        
        # Store alerts in database
        moon_count = _store_moon_alerts(moon_alerts)
        rug_count = _store_rug_alerts(rug_alerts)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Combined daily scan completed: {moon_count} moon + {rug_count} rug alerts in {duration:.1f}s")
        
        return {
            "status": "success",
            "moon_alerts": moon_count,
            "rug_alerts": rug_count,
            "total_alerts": moon_count + rug_count,
            "duration_seconds": duration,
            "symbols_scanned": len(SCAN_SYMBOLS)
        }
        
    except Exception as e:
        logger.error(f"Combined daily scan failed: {e}")
        raise self.retry(countdown=300, exc=e)


async def _run_moon_scan() -> List[MoonAlert]:
    """Run moon pattern scan on all symbols"""
    alerts = []
    
    async with MoonAnalyzer() as analyzer:
        # Process symbols in batches to avoid overwhelming APIs
        batch_size = 10
        for i in range(0, len(SCAN_SYMBOLS), batch_size):
            batch = SCAN_SYMBOLS[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                analyzer.analyze_moon_potential(symbol)
                for symbol in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect successful alerts
            for result in batch_results:
                if isinstance(result, MoonAlert):
                    alerts.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in moon scan batch: {result}")
            
            # Small delay between batches to respect rate limits
            await asyncio.sleep(0.5)
    
    return alerts


async def _run_rug_scan() -> List[RugAlert]:
    """Run rug pattern scan on all symbols"""
    alerts = []
    
    async with RugAnalyzer() as analyzer:
        # Process symbols in batches to avoid overwhelming APIs
        batch_size = 10
        for i in range(0, len(SCAN_SYMBOLS), batch_size):
            batch = SCAN_SYMBOLS[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                analyzer.analyze_rug_potential(symbol)
                for symbol in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect successful alerts
            for result in batch_results:
                if isinstance(result, RugAlert):
                    alerts.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in rug scan batch: {result}")
            
            # Small delay between batches to respect rate limits
            await asyncio.sleep(0.5)
    
    return alerts


async def _run_combined_scan() -> tuple[List[MoonAlert], List[RugAlert]]:
    """Run both moon and rug scans efficiently"""
    moon_alerts = []
    rug_alerts = []
    
    # Run both analyzers concurrently
    async with MoonAnalyzer() as moon_analyzer, RugAnalyzer() as rug_analyzer:
        # Process symbols in batches
        batch_size = 10
        for i in range(0, len(SCAN_SYMBOLS), batch_size):
            batch = SCAN_SYMBOLS[i:i + batch_size]
            
            # Create tasks for both moon and rug analysis
            moon_tasks = [moon_analyzer.analyze_moon_potential(symbol) for symbol in batch]
            rug_tasks = [rug_analyzer.analyze_rug_potential(symbol) for symbol in batch]
            
            # Run all tasks concurrently
            all_tasks = moon_tasks + rug_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # Split results back into moon and rug
            moon_results = results[:len(moon_tasks)]
            rug_results = results[len(moon_tasks):]
            
            # Collect successful alerts
            for result in moon_results:
                if isinstance(result, MoonAlert):
                    moon_alerts.append(result)
                    
            for result in rug_results:
                if isinstance(result, RugAlert):
                    rug_alerts.append(result)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    return moon_alerts, rug_alerts


def _store_moon_alerts(alerts: List[MoonAlert]) -> int:
    """Store moon alerts in database"""
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
                recommendation="MODERATE_BUY",  # Moon alerts are buy signals
                confidence_score=alert.confidence,
                
                # Component scores
                technical_score=alert.technical_score,
                news_sentiment_score=alert.sentiment_score,
                social_sentiment_score=alert.social_score,
                earnings_score=alert.earnings_score,
                market_trend_score=50.0,  # Default
                
                # Moon-specific fields
                alert_type=AlertType.MOON,
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
        logger.info(f"Stored {stored_count} moon alerts")
        
    except Exception as e:
        logger.error(f"Error storing moon alerts: {e}")
        db.rollback()
    finally:
        db.close()
        
    return stored_count


def _store_rug_alerts(alerts: List[RugAlert]) -> int:
    """Store rug alerts in database"""
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
                recommendation="MODERATE_SELL",  # Rug alerts are sell signals
                confidence_score=alert.confidence,
                
                # Component scores
                technical_score=alert.technical_score,
                news_sentiment_score=alert.sentiment_score,
                social_sentiment_score=alert.social_score,
                earnings_score=alert.earnings_score,
                market_trend_score=50.0,  # Default
                
                # Rug-specific fields
                alert_type=AlertType.RUG,
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
        logger.info(f"Stored {stored_count} rug alerts")
        
    except Exception as e:
        logger.error(f"Error storing rug alerts: {e}")
        db.rollback()
    finally:
        db.close()
        
    return stored_count
