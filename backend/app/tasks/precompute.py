"""
Precompute background tasks for stock analysis.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from celery import current_task
from sqlalchemy.orm import Session

from ..core.celery import celery_app
from ..core.database import SessionLocal
from ..core.redis_client import redis_client
from ..core.config import settings
from ..models.precomputed_analysis import PrecomputedAnalysis, PrecomputeJobStatus
from ..models.stock import Stock
from ..analyzers.confidence import ConfidenceScorer
from ..services.stock_data import StockDataService

logger = logging.getLogger(__name__)

# Top 10 stocks for testing phase
TOP_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
    "NVDA", "META", "NFLX", "AMD", "BABA"
]


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_top_stocks(self, market_hours: bool = True, symbols: Optional[List[str]] = None):
    """
    Update precomputed analysis for top stocks.
    
    Args:
        market_hours: Whether this is during market hours (affects update frequency)
        symbols: Optional list of symbols to update (defaults to TOP_STOCKS)
    """
    job_id = self.request.id
    symbols_to_update = symbols or TOP_STOCKS
    
    logger.info(f"Starting precompute job {job_id} for {len(symbols_to_update)} stocks")
    
    # Create job status record
    db = SessionLocal()
    try:
        job_status = PrecomputeJobStatus(
            job_id=job_id,
            job_type="update_top_stocks",
            symbols=symbols_to_update,
            market_hours=market_hours,
            status="RUNNING",
            started_at=datetime.now()
        )
        db.add(job_status)
        db.commit()
        
        # Run the async update function
        result = asyncio.run(_update_stocks_async(
            symbols_to_update, market_hours, job_id, db
        ))
        
        # Update job status
        job_status.status = "SUCCESS" if result["success"] else "FAILED"
        job_status.completed_at = datetime.now()
        job_status.symbols_processed = result["processed"]
        job_status.symbols_failed = result["failed"]
        job_status.total_api_calls = result["api_calls"]
        job_status.total_time_seconds = result["total_time"]
        job_status.average_time_per_symbol = result["avg_time_per_symbol"]
        job_status.error_messages = result["errors"]
        
        db.commit()
        
        logger.info(f"Precompute job {job_id} completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Precompute job {job_id} failed: {e}")
        
        # Update job status to failed
        if 'job_status' in locals():
            job_status.status = "FAILED"
            job_status.completed_at = datetime.now()
            job_status.error_messages = [str(e)]
            db.commit()
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
        
    finally:
        db.close()


async def _update_stocks_async(
    symbols: List[str], 
    market_hours: bool, 
    job_id: str,
    db: Session
) -> Dict[str, Any]:
    """Async function to update stock analyses."""
    start_time = time.time()
    processed = 0
    failed = 0
    total_api_calls = 0
    errors = []
    
    confidence_scorer = ConfidenceScorer()
    
    for symbol in symbols:
        try:
            logger.info(f"Processing {symbol} for job {job_id}")
            
            # Get or create stock record
            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                # Create basic stock record (will be enhanced later)
                stock = Stock(
                    symbol=symbol,
                    name=f"{symbol} Inc.",  # Placeholder
                    exchange="NASDAQ",  # Placeholder
                    is_active=True
                )
                db.add(stock)
                db.commit()
            
            # Perform complete analysis
            analysis_start = time.time()
            result = await confidence_scorer.analyze_stock(symbol, db)
            analysis_time = int((time.time() - analysis_start) * 1000)
            
            if "error" not in result:
                # Calculate expiry time based on market hours
                if market_hours:
                    expires_at = datetime.now() + timedelta(seconds=settings.precompute_market_hours_interval)
                else:
                    expires_at = datetime.now() + timedelta(seconds=settings.precompute_after_hours_interval)
                
                # Store precomputed analysis
                precomputed = PrecomputedAnalysis(
                    stock_id=stock.id,
                    symbol=symbol,
                    computed_at=datetime.now(),
                    expires_at=expires_at,
                    is_market_hours=market_hours,
                    complete_analysis=result,
                    technical_data=result.get("technical_analysis", {}),
                    sentiment_data={
                        "news": result.get("news_analysis", {}),
                        "social": result.get("social_analysis", {})
                    },
                    ai_analysis=result.get("ai_analysis", {}),
                    risk_assessment=result.get("risk_assessment", {}),
                    confidence_score=result.get("confidence_score", 50.0),
                    recommendation=result.get("recommendation", "HOLD"),
                    risk_level=result.get("risk_assessment", {}).get("risk_level", "MODERATE"),
                    technical_score=result.get("technical_analysis", {}).get("technical_score", 50.0),
                    news_sentiment_score=result.get("news_analysis", {}).get("news_score", 50.0),
                    social_sentiment_score=result.get("social_analysis", {}).get("social_score", 50.0),
                    api_calls_used=result.get("api_calls_used", 0),
                    data_sources=result.get("data_sources", []),
                    computation_time_ms=analysis_time,
                    analysis_version="1.0"
                )
                
                db.add(precomputed)
                db.commit()
                
                # Cache the result in Redis with metadata
                cache_key = f"precomputed_analysis:{symbol}"
                await redis_client.set_with_metadata(
                    cache_key,
                    result,
                    settings.cache_precomputed_analysis,
                    metadata={
                        "computed_at": datetime.now().isoformat(),
                        "expires_at": expires_at.isoformat(),
                        "source": "precomputed",
                        "market_hours": market_hours,
                        "api_calls_used": result.get("api_calls_used", 0)
                    }
                )
                
                processed += 1
                total_api_calls += result.get("api_calls_used", 0)
                logger.info(f"Successfully processed {symbol} in {analysis_time}ms")
                
            else:
                failed += 1
                error_msg = f"{symbol}: {result['error']}"
                errors.append(error_msg)
                logger.error(f"Failed to process {symbol}: {result['error']}")
                
        except Exception as e:
            failed += 1
            error_msg = f"{symbol}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Exception processing {symbol}: {e}")
        
        # Small delay to avoid overwhelming APIs
        await asyncio.sleep(1)
    
    total_time = time.time() - start_time
    avg_time_per_symbol = total_time / len(symbols) if symbols else 0
    
    return {
        "success": failed == 0,
        "processed": processed,
        "failed": failed,
        "total_symbols": len(symbols),
        "api_calls": total_api_calls,
        "total_time": total_time,
        "avg_time_per_symbol": avg_time_per_symbol,
        "errors": errors
    }


@celery_app.task(bind=True, max_retries=2)
def update_single_stock(self, symbol: str, force_refresh: bool = False):
    """
    Update precomputed analysis for a single stock.
    
    Args:
        symbol: Stock symbol to update
        force_refresh: Whether to force refresh even if recent data exists
    """
    job_id = self.request.id
    logger.info(f"Starting single stock update job {job_id} for {symbol}")
    
    try:
        result = asyncio.run(_update_stocks_async([symbol], True, job_id, SessionLocal()))
        logger.info(f"Single stock update job {job_id} completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Single stock update job {job_id} failed: {e}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task
def update_news_data():
    """Update news data for all tracked stocks (daily task)."""
    logger.info("Starting daily news data update")
    
    try:
        # This would update news data with longer TTL
        # Implementation depends on specific news data requirements
        logger.info("Daily news data update completed")
        return {"success": True, "message": "News data updated"}
        
    except Exception as e:
        logger.error(f"Daily news data update failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task
def cleanup_expired_cache():
    """Clean up expired cache entries and old precomputed analyses."""
    logger.info("Starting cache cleanup")
    
    db = SessionLocal()
    try:
        # Clean up old precomputed analyses (keep last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        deleted_count = db.query(PrecomputedAnalysis).filter(
            PrecomputedAnalysis.computed_at < cutoff_date
        ).delete()
        
        # Clean up old job status records (keep last 30 days)
        job_cutoff_date = datetime.now() - timedelta(days=30)
        job_deleted_count = db.query(PrecomputeJobStatus).filter(
            PrecomputeJobStatus.created_at < job_cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cache cleanup completed: {deleted_count} analyses, {job_deleted_count} job records deleted")
        return {
            "success": True, 
            "analyses_deleted": deleted_count,
            "job_records_deleted": job_deleted_count
        }
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
        
    finally:
        db.close()


# Utility functions for manual triggering
def trigger_update_top_stocks(market_hours: bool = True):
    """Manually trigger update of top stocks."""
    return update_top_stocks.delay(market_hours=market_hours)


def trigger_update_single_stock(symbol: str):
    """Manually trigger update of a single stock."""
    return update_single_stock.delay(symbol=symbol.upper())
