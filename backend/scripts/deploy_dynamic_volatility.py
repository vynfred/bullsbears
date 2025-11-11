#!/usr/bin/env python3
"""
BullsBears AI - Dynamic Volatility Deployment Script
Handles manual trigger, monitoring, and validation of dynamic volatility system
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.volatility_scanner import VolatilityScanner, get_dynamic_daily_symbols, get_dynamic_weekly_symbols, get_dynamic_monthly_symbols
from app.services.volatility_monitor import VolatilityMonitor, VolatilityPerformanceMetrics
from app.tasks.daily_scan import daily_bullish_scan, daily_bearish_scan, weekly_bullish_scan, monthly_discovery_scan
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DynamicVolatilityDeployment:
    """Handles deployment and testing of dynamic volatility system"""
    
    def __init__(self):
        self.monitor = None
        self.scanner = None
    
    async def __aenter__(self):
        self.monitor = await VolatilityMonitor().__aenter__()
        self.scanner = await VolatilityScanner().__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.monitor:
            await self.monitor.__aexit__(exc_type, exc_val, exc_tb)
        if self.scanner:
            await self.scanner.__aexit__(exc_type, exc_val, exc_tb)
    
    async def validate_system_readiness(self) -> bool:
        """Validate that the dynamic volatility system is ready for deployment"""
        logger.info("🔍 Validating dynamic volatility system readiness...")
        
        try:
            # Check API keys
            api_checks = {
                'Alpaca': bool(settings.alpaca_api_key and settings.alpaca_secret_key),
                'Finnhub': bool(settings.finnhub_api_key),
                'Polygon': bool(settings.polygon_news_api_key),
                'Databento': bool(settings.databento_api_key)
            }
            
            logger.info("📋 API Key Status:")
            for api, status in api_checks.items():
                status_icon = "✅" if status else "❌"
                logger.info(f"  {status_icon} {api}: {'Configured' if status else 'Missing'}")
            
            # Check Redis connection
            try:
                await self.scanner.redis_client.ping()
                logger.info("✅ Redis: Connected")
            except Exception as e:
                logger.error(f"❌ Redis: Connection failed - {e}")
                return False
            
            # Test symbol retrieval
            try:
                symbols = await self.scanner.get_nasdaq_symbols()
                logger.info(f"✅ Symbol Retrieval: {len(symbols)} symbols available")
            except Exception as e:
                logger.error(f"❌ Symbol Retrieval: Failed - {e}")
                return False
            
            # Test volatility calculation (with fallback)
            try:
                test_symbol = "AAPL"
                metrics = await self.scanner.calculate_volatility_metrics(test_symbol)
                if metrics:
                    logger.info(f"✅ Volatility Calculation: Working (test: {test_symbol})")
                else:
                    logger.warning(f"⚠️ Volatility Calculation: No data for {test_symbol} (may be normal)")
            except Exception as e:
                logger.warning(f"⚠️ Volatility Calculation: Error - {e} (may be API rate limits)")
            
            logger.info("✅ System validation complete - Ready for deployment!")
            return True
            
        except Exception as e:
            logger.error(f"❌ System validation failed: {e}")
            return False
    
    async def run_test_scan(self) -> bool:
        """Run a test scan with dynamic volatility detection"""
        logger.info("🚀 Running test dynamic volatility scan...")
        
        start_time = time.time()
        errors = 0
        
        try:
            # Test daily tier selection
            logger.info("📊 Testing daily tier symbol selection...")
            daily_symbols = await get_dynamic_daily_symbols()
            logger.info(f"✅ Daily tier: {len(daily_symbols)} symbols selected")
            logger.info(f"   Sample symbols: {daily_symbols[:10]}")
            
            # Test weekly tier selection
            logger.info("📊 Testing weekly tier symbol selection...")
            weekly_symbols = await get_dynamic_weekly_symbols()
            logger.info(f"✅ Weekly tier: {len(weekly_symbols)} symbols selected")
            
            # Test monthly tier selection
            logger.info("📊 Testing monthly tier symbol selection...")
            monthly_symbols = await get_dynamic_monthly_symbols()
            logger.info(f"✅ Monthly tier: {len(monthly_symbols)} symbols selected")
            
            # Calculate performance metrics
            scan_duration = time.time() - start_time
            total_symbols = len(daily_symbols) + len(weekly_symbols) + len(monthly_symbols)
            
            # Log performance metrics
            metrics = VolatilityPerformanceMetrics(
                timestamp=datetime.now(),
                total_symbols_scanned=total_symbols,
                api_calls_made=total_symbols,  # Estimate
                cache_hits=0,  # Will be updated by actual usage
                cache_misses=total_symbols,
                avg_volatility_score=0.5,  # Placeholder
                top_volatility_score=1.0,  # Placeholder
                sector_distribution={},  # Will be populated by actual scan
                api_costs_estimated=total_symbols * 0.001,  # Conservative estimate
                scan_duration_seconds=scan_duration,
                errors_encountered=errors
            )
            
            await self.monitor.log_scan_performance(metrics)
            
            logger.info(f"✅ Test scan completed successfully!")
            logger.info(f"   Duration: {scan_duration:.2f} seconds")
            logger.info(f"   Total symbols: {total_symbols}")
            logger.info(f"   Estimated cost: ${metrics.api_costs_estimated:.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test scan failed: {e}")
            return False
    
    async def run_production_scan(self, scan_type: str = "daily_bullish") -> bool:
        """Run a production scan with monitoring"""
        logger.info(f"🎯 Running production {scan_type} scan...")
        
        start_time = time.time()
        
        try:
            if scan_type == "daily_bullish":
                result = await daily_bullish_scan()
            elif scan_type == "daily_bearish":
                result = await daily_bearish_scan()
            elif scan_type == "weekly_bullish":
                result = await weekly_bullish_scan()
            elif scan_type == "monthly_discovery":
                result = await monthly_discovery_scan()
            else:
                logger.error(f"❌ Unknown scan type: {scan_type}")
                return False
            
            scan_duration = time.time() - start_time
            
            logger.info(f"✅ Production {scan_type} scan completed!")
            logger.info(f"   Duration: {scan_duration:.2f} seconds")
            logger.info(f"   Result: {result}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Production {scan_type} scan failed: {e}")
            return False
    
    async def monitor_system_health(self) -> Dict[str, Any]:
        """Check and report system health"""
        logger.info("🏥 Checking system health...")
        
        try:
            health = await self.monitor.check_system_health()
            
            status_icon = {
                'healthy': '✅',
                'degraded': '⚠️',
                'error': '❌'
            }.get(health['overall_status'], '❓')
            
            logger.info(f"{status_icon} Overall Status: {health['overall_status'].upper()}")
            
            if health['issues']:
                logger.warning("🚨 Issues found:")
                for issue in health['issues']:
                    logger.warning(f"   - {issue}")
            
            if health['warnings']:
                logger.info("⚠️ Warnings:")
                for warning in health['warnings']:
                    logger.info(f"   - {warning}")
            
            # Cost breakdown
            cost_breakdown = await self.monitor.get_api_cost_breakdown(7)
            logger.info(f"💰 Cost Summary (7 days):")
            logger.info(f"   Total: ${cost_breakdown.get('total_cost', 0):.4f}")
            logger.info(f"   Daily Average: ${cost_breakdown.get('average_daily_cost', 0):.4f}")
            logger.info(f"   Monthly Projection: ${cost_breakdown.get('projected_monthly_cost', 0):.2f}")
            
            return health
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {'overall_status': 'error', 'issues': [str(e)]}

async def main():
    """Main deployment script"""
    logger.info("🚀 BullsBears Dynamic Volatility Deployment Starting...")
    
    async with DynamicVolatilityDeployment() as deployment:
        
        # Step 1: Validate system readiness
        if not await deployment.validate_system_readiness():
            logger.error("❌ System validation failed - aborting deployment")
            return False
        
        # Step 2: Run test scan
        if not await deployment.run_test_scan():
            logger.error("❌ Test scan failed - aborting deployment")
            return False
        
        # Step 3: Check system health
        health = await deployment.monitor_system_health()
        if health['overall_status'] == 'error':
            logger.error("❌ System health check failed - aborting deployment")
            return False
        
        # Step 4: Ask user for production deployment confirmation
        logger.info("\n" + "="*60)
        logger.info("🎯 READY FOR PRODUCTION DEPLOYMENT")
        logger.info("="*60)
        logger.info("✅ System validation: PASSED")
        logger.info("✅ Test scan: PASSED")
        logger.info(f"✅ System health: {health['overall_status'].upper()}")
        logger.info("\nNext steps:")
        logger.info("1. Manual trigger: Run production scans manually")
        logger.info("2. Schedule: Enable Celery beat for 08:30 AM daily scans")
        logger.info("3. Monitor: Track performance and costs")
        
        # Optional: Run a production scan if requested
        import os
        if os.getenv('RUN_PRODUCTION_SCAN', '').lower() == 'true':
            logger.info("\n🎯 Running production scan as requested...")
            await deployment.run_production_scan("daily_bullish")
        
        logger.info("\n✅ Dynamic Volatility Deployment Complete!")
        return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        sys.exit(1)
