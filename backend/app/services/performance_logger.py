"""
Performance Logger Service for BullsBears.xyz ML Data Collection
Handles async logging of dual AI performance metrics with <10ms write performance
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.analysis_results import AnalysisResult
from ..services.ai_consensus import ConsensusResult, AgreementLevel
from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for dual AI analysis."""
    symbol: str
    analysis_id: int
    response_time_ms: int
    cache_hit: bool
    ai_cost_cents: int
    grok_analysis_time: Optional[datetime]
    deepseek_analysis_time: Optional[datetime]
    consensus_time: Optional[datetime]
    handoff_delta: Optional[float]
    ml_features: Dict[str, Any]
    consensus_score: float
    api_calls_count: int
    data_sources_used: List[str]
    performance_tier: str
    agreement_level: str
    confidence_adjustment: float

class PerformanceLogger:
    """Async performance logger for ML data collection."""
    
    def __init__(self):
        self.redis_client = None
        self.performance_queue = asyncio.Queue()
        self.batch_size = 10
        self.batch_timeout = 5.0  # seconds
        self.running = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.redis_client = await get_redis_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.running:
            await self.stop_batch_processor()
    
    async def start_batch_processor(self):
        """Start the batch processing task."""
        if not self.running:
            self.running = True
            asyncio.create_task(self._batch_processor())
            logger.info("Performance logger batch processor started")
    
    async def stop_batch_processor(self):
        """Stop the batch processing task."""
        self.running = False
        # Process remaining items in queue
        await self._flush_queue()
        logger.info("Performance logger batch processor stopped")
    
    async def log_dual_ai_performance(self, 
                                    symbol: str,
                                    analysis_id: int,
                                    consensus_result: ConsensusResult,
                                    start_time: float,
                                    grok_start_time: Optional[float] = None,
                                    deepseek_start_time: Optional[float] = None,
                                    consensus_start_time: Optional[float] = None,
                                    cache_hit: bool = False,
                                    api_calls_count: int = 0,
                                    data_sources: List[str] = None,
                                    ml_context: Dict[str, Any] = None) -> None:
        """
        Log dual AI performance metrics asynchronously.
        Target: <10ms execution time for non-blocking operation.
        """
        try:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            # Calculate phase timings
            grok_analysis_time = None
            deepseek_analysis_time = None
            consensus_time = None
            handoff_delta = None
            
            if grok_start_time:
                grok_analysis_time = datetime.fromtimestamp(grok_start_time)
            if deepseek_start_time:
                deepseek_analysis_time = datetime.fromtimestamp(deepseek_start_time)
                if grok_start_time:
                    handoff_delta = deepseek_start_time - grok_start_time
            if consensus_start_time:
                consensus_time = datetime.fromtimestamp(consensus_start_time)
            
            # Determine performance tier
            if response_time_ms < 200:
                performance_tier = "fast"
            elif response_time_ms < 500:
                performance_tier = "standard"
            else:
                performance_tier = "slow"
            
            # Estimate API costs (rough estimates in cents)
            grok_cost = 2 if not cache_hit else 0  # ~2 cents per Grok call
            deepseek_cost = 1 if not cache_hit else 0  # ~1 cent per DeepSeek call
            total_cost = grok_cost + deepseek_cost
            
            # Create performance metrics
            metrics = PerformanceMetrics(
                symbol=symbol,
                analysis_id=analysis_id,
                response_time_ms=response_time_ms,
                cache_hit=cache_hit,
                ai_cost_cents=total_cost,
                grok_analysis_time=grok_analysis_time,
                deepseek_analysis_time=deepseek_analysis_time,
                consensus_time=consensus_time,
                handoff_delta=handoff_delta,
                ml_features=ml_context or {},
                consensus_score=consensus_result.consensus_confidence,
                api_calls_count=api_calls_count,
                data_sources_used=data_sources or ["demo"],
                performance_tier=performance_tier,
                agreement_level=consensus_result.agreement_level.value,
                confidence_adjustment=consensus_result.confidence_adjustment
            )
            
            # Queue for async batch processing
            await self.performance_queue.put(metrics)
            
            # Cache performance metrics for real-time monitoring
            if self.redis_client:
                cache_key = f"perf_metrics:{symbol}:{analysis_id}"
                await self.redis_client.setex(
                    cache_key, 
                    3600,  # 1 hour TTL
                    str(asdict(metrics))
                )
            
            logger.debug(f"Queued performance metrics for {symbol} (ID: {analysis_id})")
            
        except Exception as e:
            logger.error(f"Error logging performance metrics: {e}")
    
    async def _batch_processor(self):
        """Process performance metrics in batches for efficiency."""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Wait for items with timeout
                try:
                    metrics = await asyncio.wait_for(
                        self.performance_queue.get(), 
                        timeout=1.0
                    )
                    batch.append(metrics)
                except asyncio.TimeoutError:
                    pass
                
                # Flush batch if size or time threshold reached
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_flush >= self.batch_timeout)
                )
                
                if should_flush:
                    await self._flush_batch(batch)
                    batch.clear()
                    last_flush = current_time
                    
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)
        
        # Final flush
        if batch:
            await self._flush_batch(batch)
    
    async def _flush_batch(self, batch: List[PerformanceMetrics]):
        """Flush a batch of performance metrics to database."""
        if not batch:
            return
            
        try:
            # Use raw SQL for maximum performance
            db = next(get_db())
            
            # Build batch update query
            update_values = []
            for metrics in batch:
                update_values.append(f"""
                    ({metrics.analysis_id}, {metrics.response_time_ms}, 
                     {metrics.cache_hit}, {metrics.ai_cost_cents},
                     {f"'{metrics.grok_analysis_time}'" if metrics.grok_analysis_time else 'NULL'},
                     {f"'{metrics.deepseek_analysis_time}'" if metrics.deepseek_analysis_time else 'NULL'},
                     {f"'{metrics.consensus_time}'" if metrics.consensus_time else 'NULL'},
                     {metrics.handoff_delta if metrics.handoff_delta else 'NULL'},
                     '{str(metrics.ml_features).replace("'", "''")}',
                     {metrics.consensus_score}, {metrics.api_calls_count},
                     '{str(metrics.data_sources_used).replace("'", "''")}',
                     '{metrics.performance_tier}')
                """)
            
            # Execute batch update
            query = f"""
                UPDATE analysis_results 
                SET response_time_ms = batch.response_time_ms,
                    cache_hit = batch.cache_hit,
                    ai_cost_cents = batch.ai_cost_cents,
                    grok_analysis_time = batch.grok_analysis_time,
                    deepseek_analysis_time = batch.deepseek_analysis_time,
                    consensus_time = batch.consensus_time,
                    handoff_delta = batch.handoff_delta,
                    ml_features = batch.ml_features::jsonb,
                    consensus_score = batch.consensus_score,
                    api_calls_count = batch.api_calls_count,
                    data_sources_used = batch.data_sources_used::jsonb,
                    performance_tier = batch.performance_tier
                FROM (VALUES {','.join(update_values)}) AS batch(
                    id, response_time_ms, cache_hit, ai_cost_cents,
                    grok_analysis_time, deepseek_analysis_time, consensus_time,
                    handoff_delta, ml_features, consensus_score, api_calls_count,
                    data_sources_used, performance_tier
                )
                WHERE analysis_results.id = batch.id
            """
            
            db.execute(text(query))
            db.commit()
            
            logger.info(f"Flushed {len(batch)} performance metrics to database")
            
        except Exception as e:
            logger.error(f"Error flushing performance batch: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()
    
    async def _flush_queue(self):
        """Flush all remaining items in the queue."""
        batch = []
        while not self.performance_queue.empty():
            try:
                metrics = self.performance_queue.get_nowait()
                batch.append(metrics)
            except asyncio.QueueEmpty:
                break
        
        if batch:
            await self._flush_batch(batch)
    
    async def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get performance summary for the last N days."""
        try:
            db = next(get_db())
            
            query = text("""
                SELECT 
                    COUNT(*) as total_analyses,
                    AVG(response_time_ms) as avg_response_time,
                    MIN(response_time_ms) as min_response_time,
                    MAX(response_time_ms) as max_response_time,
                    SUM(ai_cost_cents) as total_cost_cents,
                    AVG(ai_cost_cents) as avg_cost_per_analysis,
                    COUNT(CASE WHEN cache_hit = TRUE THEN 1 END) as cache_hits,
                    COUNT(CASE WHEN cache_hit = FALSE THEN 1 END) as cache_misses,
                    COUNT(CASE WHEN agreement_level = 'strong_agreement' THEN 1 END) as strong_agreements,
                    COUNT(CASE WHEN agreement_level = 'partial_agreement' THEN 1 END) as partial_agreements,
                    COUNT(CASE WHEN agreement_level = 'strong_disagreement' THEN 1 END) as strong_disagreements,
                    COUNT(CASE WHEN performance_tier = 'fast' THEN 1 END) as fast_analyses,
                    COUNT(CASE WHEN performance_tier = 'standard' THEN 1 END) as standard_analyses,
                    COUNT(CASE WHEN performance_tier = 'slow' THEN 1 END) as slow_analyses
                FROM analysis_results 
                WHERE created_at >= NOW() - INTERVAL '%s days'
                  AND response_time_ms IS NOT NULL
            """)
            
            result = db.execute(query, (days,)).fetchone()
            
            if result:
                total = result.total_analyses or 0
                cache_total = (result.cache_hits or 0) + (result.cache_misses or 0)
                
                return {
                    "total_analyses": total,
                    "avg_response_time_ms": round(result.avg_response_time or 0, 2),
                    "min_response_time_ms": result.min_response_time or 0,
                    "max_response_time_ms": result.max_response_time or 0,
                    "total_cost_cents": result.total_cost_cents or 0,
                    "avg_cost_per_analysis": round(result.avg_cost_per_analysis or 0, 2),
                    "cache_hit_rate": round((result.cache_hits or 0) * 100.0 / max(cache_total, 1), 2),
                    "agreement_distribution": {
                        "strong_agreement": result.strong_agreements or 0,
                        "partial_agreement": result.partial_agreements or 0,
                        "strong_disagreement": result.strong_disagreements or 0
                    },
                    "performance_distribution": {
                        "fast": result.fast_analyses or 0,
                        "standard": result.standard_analyses or 0,
                        "slow": result.slow_analyses or 0
                    }
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
        finally:
            if db:
                db.close()

# Global performance logger instance
performance_logger = PerformanceLogger()

async def log_dual_ai_performance(*args, **kwargs):
    """Convenience function for logging performance metrics."""
    await performance_logger.log_dual_ai_performance(*args, **kwargs)
