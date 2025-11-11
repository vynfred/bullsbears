"""
API Usage Tracking Service
Tracks API calls and data usage for cost monitoring and 20GB FMP threshold
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncpg
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class APIUsageTracker:
    """
    Tracks API usage for cost control and data threshold monitoring
    
    Key Features:
    - Track FMP API calls and estimate data usage toward 20GB monthly limit
    - Track RunPod GPU usage and costs
    - Track cloud API calls (Groq, Grok, DeepSeek, etc.)
    - Monthly reset and historical tracking
    """
    
    def __init__(self):
        self.db_pool = None
    
    async def initialize(self):
        """Initialize database connection and create tables if needed"""
        try:
            self.db_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=1,
                max_size=5
            )
            
            # Create API usage tracking table
            await self.create_usage_table()
            logger.info("✅ API Usage Tracker initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize API Usage Tracker: {e}")
            raise
    
    async def create_usage_table(self):
        """Create API usage tracking table"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage_log (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,  -- 'FMP', 'RunPod', 'Groq', 'Grok', etc.
                    endpoint VARCHAR(200),          -- API endpoint called
                    method VARCHAR(10) DEFAULT 'GET',
                    response_size_bytes INTEGER DEFAULT 0,
                    cost_usd DECIMAL(10,4) DEFAULT 0.0,
                    success BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'     -- Additional tracking data
                );
                
                CREATE INDEX IF NOT EXISTS idx_api_usage_provider_date 
                ON api_usage_log(provider, created_at);
                
                CREATE INDEX IF NOT EXISTS idx_api_usage_monthly 
                ON api_usage_log(date_trunc('month', created_at));
            """)
    
    async def log_api_call(
        self, 
        provider: str, 
        endpoint: str = None,
        method: str = "GET",
        response_size_bytes: int = 0,
        cost_usd: float = 0.0,
        success: bool = True,
        metadata: Dict[str, Any] = None
    ):
        """Log an API call for usage tracking"""
        if not self.db_pool:
            return  # Not initialized yet
            
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO api_usage_log 
                    (provider, endpoint, method, response_size_bytes, cost_usd, success, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, provider, endpoint, method, response_size_bytes, cost_usd, success, 
                json.dumps(metadata or {}))
                
        except Exception as e:
            logger.error(f"Failed to log API call: {e}")
    
    async def get_fmp_usage_this_month(self) -> Dict[str, Any]:
        """Get FMP usage for current month toward 20GB limit"""
        if not self.db_pool:
            return {"error": "Not initialized"}
            
        try:
            async with self.db_pool.acquire() as conn:
                # Get this month's FMP usage
                result = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as calls_count,
                        SUM(response_size_bytes) as total_bytes,
                        SUM(cost_usd) as total_cost
                    FROM api_usage_log 
                    WHERE provider = 'FMP' 
                    AND created_at >= date_trunc('month', CURRENT_DATE)
                """)
                
                calls_count = result['calls_count'] or 0
                total_bytes = result['total_bytes'] or 0
                total_cost = result['total_cost'] or 0.0
                
                # Convert to GB
                total_gb = total_bytes / (1024 * 1024 * 1024)
                usage_percentage = (total_gb / 20) * 100  # 20GB limit
                
                return {
                    "calls_this_month": calls_count,
                    "data_usage_gb": round(total_gb, 3),
                    "data_limit_gb": 20,
                    "usage_percentage": f"{usage_percentage:.1f}%",
                    "remaining_gb": round(20 - total_gb, 3),
                    "estimated_cost": f"${total_cost:.2f}",
                    "monthly_cost": "$29.00"
                }
                
        except Exception as e:
            logger.error(f"Failed to get FMP usage: {e}")
            return {"error": str(e)}
    
    async def get_runpod_usage_this_month(self) -> Dict[str, Any]:
        """Get RunPod usage and costs for current month"""
        if not self.db_pool:
            return {"error": "Not initialized"}
            
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as calls_count,
                        SUM(cost_usd) as total_cost,
                        MAX(created_at) as last_call
                    FROM api_usage_log 
                    WHERE provider = 'RunPod' 
                    AND created_at >= date_trunc('month', CURRENT_DATE)
                """)
                
                calls_count = result['calls_count'] or 0
                total_cost = result['total_cost'] or 0.0
                last_call = result['last_call']
                
                return {
                    "sessions_this_month": calls_count,
                    "total_cost_usd": f"${total_cost:.4f}",
                    "last_session": last_call.isoformat() if last_call else None,
                    "cost_per_session": f"${(total_cost/calls_count):.4f}" if calls_count > 0 else "$0.0000"
                }
                
        except Exception as e:
            logger.error(f"Failed to get RunPod usage: {e}")
            return {"error": str(e)}
    
    async def get_cloud_api_usage(self) -> Dict[str, Any]:
        """Get usage for all cloud APIs (Groq, Grok, DeepSeek, etc.)"""
        if not self.db_pool:
            return {"error": "Not initialized"}
            
        try:
            async with self.db_pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT 
                        provider,
                        COUNT(*) as calls_count,
                        SUM(cost_usd) as total_cost
                    FROM api_usage_log 
                    WHERE provider IN ('Groq', 'Grok', 'DeepSeek', 'Gemini', 'Claude', 'OpenAI')
                    AND created_at >= date_trunc('month', CURRENT_DATE)
                    GROUP BY provider
                """)
                
                usage = {}
                for row in results:
                    usage[row['provider'].lower()] = {
                        "calls_this_month": row['calls_count'],
                        "cost_this_month": f"${row['total_cost']:.4f}"
                    }
                
                return usage
                
        except Exception as e:
            logger.error(f"Failed to get cloud API usage: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close database connections"""
        if self.db_pool:
            await self.db_pool.close()

# Global instance
api_usage_tracker = APIUsageTracker()

async def get_api_usage_tracker() -> APIUsageTracker:
    """Get initialized API usage tracker"""
    if not api_usage_tracker.db_pool:
        await api_usage_tracker.initialize()
    return api_usage_tracker
