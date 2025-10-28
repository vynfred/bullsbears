#!/usr/bin/env python3
"""
Historical Data Backfill Script for BullsBears.xyz
Generates 50 realistic stock analysis simulations for ML training and cost monitoring
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import numpy as np
import pandas as pd

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.models.analysis_results import AnalysisResult
from app.models.dual_ai_training import DualAITrainingData
from app.services.historical_data import HistoricalDataService, StockData, MarketContext
from app.services.analysis_simulator import AnalysisSimulator
from app.services.cost_monitor import CostMonitor, APIService
from app.services.performance_logger import PerformanceLogger
from app.core.redis_client import get_redis_client
import sqlalchemy as sa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLDataBackfillService:
    """Service for backfilling ML training data with realistic simulations."""
    
    def __init__(self):
        self.historical_service = HistoricalDataService()
        self.analysis_simulator = AnalysisSimulator()
        self.cost_monitor = None
        self.performance_logger = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize services without Redis for simulation
        try:
            self.cost_monitor = CostMonitor()
            await self.cost_monitor.__aenter__()
        except Exception as e:
            logger.warning(f"Cost monitor initialization failed (Redis not available): {e}")
            self.cost_monitor = None

        try:
            self.performance_logger = PerformanceLogger()
            await self.performance_logger.__aenter__()
        except Exception as e:
            logger.warning(f"Performance logger initialization failed (Redis not available): {e}")
            self.performance_logger = None

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.cost_monitor:
            try:
                await self.cost_monitor.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.warning(f"Cost monitor cleanup failed: {e}")
        if self.performance_logger:
            try:
                await self.performance_logger.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.warning(f"Performance logger cleanup failed: {e}")
    
    async def backfill_analysis_data(self, num_stocks: int = 50) -> Dict[str, Any]:
        """
        Backfill database with realistic analysis data.
        
        Args:
            num_stocks: Number of stocks to analyze (default 50)
            
        Returns:
            Summary statistics of backfill operation
        """
        logger.info(f"Starting ML data backfill for {num_stocks} stocks")
        
        try:
            # Collect historical data (with fallback to synthetic data)
            logger.info("Collecting historical stock data...")
            try:
                stock_data_list = await self.historical_service.collect_historical_data(
                    symbols=None,  # Use all available symbols
                    days_back=30
                )
            except Exception as e:
                logger.warning(f"Real data collection failed: {e}")
                logger.info("Falling back to synthetic data generation...")
                stock_data_list = await self._generate_synthetic_stock_data(num_stocks)

            # Limit to requested number of stocks
            if len(stock_data_list) > num_stocks:
                stock_data_list = random.sample(stock_data_list, num_stocks)
            elif len(stock_data_list) == 0:
                logger.info("No real data available, generating synthetic data...")
                stock_data_list = await self._generate_synthetic_stock_data(num_stocks)

            logger.info(f"Collected data for {len(stock_data_list)} stocks")
            
            # Generate market context
            market_context = await self.historical_service.generate_market_context()
            logger.info(f"Generated market context: {market_context.market_trend} trend, VIX: {market_context.vix_level:.1f}")
            
            # Process each stock
            results = []
            total_cost = 0.0
            total_api_calls = 0

            # Create database session
            db = SessionLocal()
            try:
                for i, stock_data in enumerate(stock_data_list, 1):
                    try:
                        logger.info(f"Processing {stock_data.symbol} ({i}/{len(stock_data_list)})")
                        
                        # Calculate technical indicators
                        technical_indicators = self.historical_service.calculate_technical_indicators(
                            stock_data.price_data
                        )
                        
                        # Generate complete analysis simulation
                        analysis_result = await self.analysis_simulator.generate_complete_analysis(
                            stock_data, market_context, technical_indicators
                        )
                        
                        # Store in database
                        await self._store_analysis_result(db, analysis_result)
                        
                        # Track cost monitoring
                        await self._track_cost_monitoring(analysis_result)
                        
                        # Update statistics
                        total_cost += analysis_result["cost_data"]["ai_cost_cents"]
                        total_api_calls += analysis_result["cost_data"]["api_calls_count"]
                        
                        results.append({
                            "symbol": stock_data.symbol,
                            "consensus_confidence": analysis_result["consensus_result"]["consensus_confidence"],
                            "agreement_level": analysis_result["consensus_result"]["agreement_level"],
                            "cost_cents": analysis_result["cost_data"]["ai_cost_cents"],
                            "processing_time_ms": analysis_result["processing_time_ms"]
                        })
                        
                        # Rate limiting to avoid overwhelming the system
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        logger.error(f"Error processing {stock_data.symbol}: {e}")
                        continue
                
                # Commit all changes
                db.commit()

            finally:
                db.close()

            # Generate summary statistics
            summary = self._generate_summary_statistics(results, total_cost, total_api_calls)
            logger.info(f"Backfill completed successfully: {summary}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error during backfill operation: {e}")
            raise
    
    async def _store_analysis_result(self, db, analysis_result: Dict[str, Any]):
        """Store analysis result in database."""
        try:
            # Create AnalysisResult record (stock_id=1 for simulation)
            analysis_record = AnalysisResult(
                stock_id=1,  # Use dummy stock_id for simulation
                symbol=analysis_result["symbol"],
                analysis_type="dual_ai_simulation",
                timestamp=datetime.fromisoformat(analysis_result["timestamp"]),
                confidence_score=analysis_result["consensus_result"]["consensus_confidence"],
                consensus_reasoning=analysis_result["consensus_result"]["reasoning"],
                recommendation="HOLD",  # Default for simulations
                risk_level="moderate",
                # Component scores (required fields)
                technical_score=analysis_result["grok_analysis"]["confidence"],
                news_sentiment_score=analysis_result["deepseek_analysis"]["confidence"],
                social_sentiment_score=analysis_result["deepseek_analysis"]["confidence"],
                earnings_score=50.0,  # Default for simulations
                market_trend_score=50.0,  # Default for simulations
                
                # ML Performance Columns
                grok_score=analysis_result["grok_analysis"]["confidence"],
                deepseek_score=analysis_result["deepseek_analysis"]["confidence"],
                consensus_score=analysis_result["consensus_result"]["consensus_confidence"],
                agreement_level=analysis_result["consensus_result"]["agreement_level"].value,
                confidence_adjustment=analysis_result["consensus_result"]["confidence_adjustment"],
                handoff_delta=abs(analysis_result["grok_analysis"]["confidence"] - 
                                analysis_result["deepseek_analysis"]["confidence"]),
                
                # Performance Metrics
                response_time_ms=analysis_result["cost_data"]["response_time_ms"],
                cache_hit=analysis_result["cost_data"]["cache_hit"],
                ai_cost_cents=analysis_result["cost_data"]["ai_cost_cents"],
                api_calls_count=analysis_result["cost_data"]["api_calls_count"],
                data_sources_used=analysis_result["cost_data"]["data_sources_used"],
                performance_tier=analysis_result["cost_data"]["performance_tier"],
                
                # ML Features
                ml_features=analysis_result["ml_features"],
                
                # Timestamps
                created_at=datetime.fromisoformat(analysis_result["timestamp"]),
                expires_at=datetime.fromisoformat(analysis_result["timestamp"]) + timedelta(hours=24)
            )
            
            db.add(analysis_record)
            
            # Create DualAITrainingData record for ML training
            training_record = DualAITrainingData(
                analysis_result_id=None,  # Will be set after analysis_record is committed
                symbol=analysis_result["symbol"],

                # Grok AI data
                grok_recommendation="HOLD",  # Default for simulations
                grok_confidence=analysis_result["grok_analysis"]["confidence"],
                grok_reasoning=analysis_result["grok_analysis"]["reasoning"],
                grok_risk_warning=analysis_result["grok_analysis"]["risk_assessment"],

                # DeepSeek AI data
                deepseek_sentiment_score=analysis_result["deepseek_analysis"]["sentiment_score"],
                deepseek_confidence=analysis_result["deepseek_analysis"]["confidence"],
                deepseek_narrative=analysis_result["deepseek_analysis"]["reasoning"],
                deepseek_crowd_psychology="MIXED",  # Default for simulations
                deepseek_social_news_bridge=0.5,  # Default correlation

                # Consensus data
                consensus_recommendation="HOLD",  # Default for simulations
                consensus_confidence=analysis_result["consensus_result"]["consensus_confidence"],
                agreement_level=analysis_result["consensus_result"]["agreement_level"].value,
                confidence_adjustment=analysis_result["consensus_result"]["confidence_adjustment"],
                hybrid_validation_triggered=False,
                consensus_reasoning=analysis_result["consensus_result"]["reasoning"],

                # Context data as JSON strings
                market_conditions=str(analysis_result["market_context"]),
                technical_indicators=str(analysis_result["grok_analysis"]["technical_indicators"]),
                news_context=str(analysis_result["deepseek_analysis"]["news_sentiment"]),
                social_context=str(analysis_result["deepseek_analysis"]["social_sentiment"]),

                # ML metadata
                training_label="PENDING",  # To be updated when actual outcomes are known
                data_quality_score=95.0,  # High quality simulated data

                created_at=datetime.fromisoformat(analysis_result["timestamp"])
            )
            
            db.add(training_record)
            
        except Exception as e:
            logger.error(f"Error storing analysis result: {e}")
            raise
    
    async def _track_cost_monitoring(self, analysis_result: Dict[str, Any]):
        """Track cost monitoring for the analysis."""
        if not self.cost_monitor:
            logger.debug("Cost monitor not available, skipping cost tracking")
            return

        try:
            cost_data = analysis_result["cost_data"]

            # Track Grok API usage
            await self.cost_monitor.track_api_usage(
                service=APIService.GROK,
                tokens_used=cost_data["grok_tokens"],
                request_cost=cost_data["grok_cost_cents"]
            )
            
            # Track DeepSeek API usage
            await self.cost_monitor.track_api_usage(
                service=APIService.DEEPSEEK,
                tokens_used=cost_data["deepseek_tokens"],
                request_cost=cost_data["deepseek_cost_cents"]
            )
            
            # Track external API usage
            for api_name, call_count in cost_data["api_calls_breakdown"].items():
                if call_count > 0:
                    if api_name == "alpha_vantage":
                        service = APIService.ALPHA_VANTAGE
                    elif api_name == "newsapi":
                        service = APIService.NEWSAPI
                    elif api_name == "reddit":
                        service = APIService.REDDIT
                    elif api_name == "twitter":
                        service = APIService.TWITTER
                    elif api_name == "fmp":
                        service = APIService.FMP
                    else:
                        continue
                    
                    for _ in range(call_count):
                        await self.cost_monitor.track_api_usage(service=service)
            
        except Exception as e:
            logger.error(f"Error tracking cost monitoring: {e}")

    async def _generate_synthetic_stock_data(self, num_stocks: int) -> List[StockData]:
        """Generate synthetic stock data for demonstration purposes."""
        logger.info(f"Generating {num_stocks} synthetic stock data entries...")

        # Sample stock symbols and info
        sample_stocks = [
            ("AAPL", "Apple Inc.", "Technology"),
            ("MSFT", "Microsoft Corporation", "Technology"),
            ("GOOGL", "Alphabet Inc.", "Technology"),
            ("TSLA", "Tesla, Inc.", "Technology"),
            ("JPM", "JPMorgan Chase & Co.", "Finance"),
            ("BAC", "Bank of America Corporation", "Finance"),
            ("JNJ", "Johnson & Johnson", "Healthcare"),
            ("PFE", "Pfizer Inc.", "Healthcare"),
            ("AMZN", "Amazon.com, Inc.", "Consumer"),
            ("WMT", "Walmart Inc.", "Consumer"),
            ("XOM", "Exxon Mobil Corporation", "Energy"),
            ("CVX", "Chevron Corporation", "Energy"),
            ("BA", "The Boeing Company", "Industrial"),
            ("CAT", "Caterpillar Inc.", "Industrial"),
            ("SPY", "SPDR S&P 500 ETF Trust", "ETF")
        ]

        # Extend the list if we need more stocks
        while len(sample_stocks) < num_stocks:
            sample_stocks.extend(sample_stocks[:min(len(sample_stocks), num_stocks - len(sample_stocks))])

        stock_data_list = []

        for i in range(num_stocks):
            symbol, name, sector = sample_stocks[i % len(sample_stocks)]

            # Generate synthetic price data
            base_price = random.uniform(50, 500)
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')

            # Generate realistic price movements
            price_changes = np.random.normal(0, 0.02, 30)  # 2% daily volatility
            prices = [base_price]

            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1.0))  # Ensure price doesn't go negative

            # Create DataFrame with OHLC data
            price_data = pd.DataFrame({
                'Open': [p * random.uniform(0.99, 1.01) for p in prices],
                'High': [p * random.uniform(1.00, 1.03) for p in prices],
                'Low': [p * random.uniform(0.97, 1.00) for p in prices],
                'Close': prices
            }, index=dates)

            # Generate volume data
            base_volume = random.randint(1000000, 50000000)
            volumes = [base_volume * random.uniform(0.5, 2.0) for _ in range(30)]
            volume_data = pd.DataFrame({'Volume': volumes}, index=dates)

            # Create StockData object
            stock_data = StockData(
                symbol=symbol,
                company_name=name,
                sector=sector,
                price_data=price_data,
                volume_data=volume_data,
                market_cap=random.uniform(10e9, 3000e9),  # 10B to 3T market cap
                pe_ratio=random.uniform(10, 50),
                beta=random.uniform(0.5, 2.0)
            )

            stock_data_list.append(stock_data)

        logger.info(f"Generated {len(stock_data_list)} synthetic stock data entries")
        return stock_data_list
    
    def _generate_summary_statistics(self, results: List[Dict], total_cost: float, total_api_calls: int) -> Dict[str, Any]:
        """Generate summary statistics for the backfill operation."""
        if not results:
            return {"error": "No results to summarize"}
        
        # Calculate statistics
        confidences = [r["consensus_confidence"] for r in results]
        costs = [r["cost_cents"] for r in results]
        processing_times = [r["processing_time_ms"] for r in results]
        
        # Agreement level distribution
        agreement_levels = [r["agreement_level"] for r in results]
        agreement_dist = {
            "strong_agreement": agreement_levels.count("strong_agreement"),
            "partial_agreement": agreement_levels.count("partial_agreement"),
            "disagreement": agreement_levels.count("disagreement")
        }
        
        return {
            "total_analyses": len(results),
            "total_cost_cents": round(total_cost, 2),
            "total_cost_usd": round(total_cost / 100, 2),
            "total_api_calls": total_api_calls,
            "avg_confidence": round(sum(confidences) / len(confidences), 3),
            "avg_cost_per_analysis": round(sum(costs) / len(costs), 2),
            "avg_processing_time_ms": round(sum(processing_times) / len(processing_times), 1),
            "agreement_distribution": agreement_dist,
            "confidence_range": {
                "min": round(min(confidences), 3),
                "max": round(max(confidences), 3)
            },
            "cost_range": {
                "min": round(min(costs), 2),
                "max": round(max(costs), 2)
            }
        }

async def main():
    """Main execution function for the backfill script."""
    logger.info("Starting BullsBears.xyz ML Data Backfill")

    try:
        async with MLDataBackfillService() as backfill_service:
            # Run backfill for 5 stocks (testing)
            summary = await backfill_service.backfill_analysis_data(num_stocks=5)

            # Print summary
            print("\n" + "="*60)
            print("BACKFILL SUMMARY")
            print("="*60)
            print(f"Total Analyses: {summary['total_analyses']}")
            print(f"Total Cost: ${summary['total_cost_usd']:.2f} ({summary['total_cost_cents']:.0f} cents)")
            print(f"Total API Calls: {summary['total_api_calls']}")
            print(f"Average Confidence: {summary['avg_confidence']:.3f}")
            print(f"Average Cost per Analysis: {summary['avg_cost_per_analysis']:.2f} cents")
            print(f"Average Processing Time: {summary['avg_processing_time_ms']:.1f}ms")
            print("\nAgreement Distribution:")
            for level, count in summary['agreement_distribution'].items():
                percentage = (count / summary['total_analyses']) * 100
                print(f"  {level}: {count} ({percentage:.1f}%)")
            print("\nConfidence Range:")
            print(f"  Min: {summary['confidence_range']['min']:.3f}")
            print(f"  Max: {summary['confidence_range']['max']:.3f}")
            print("\nCost Range:")
            print(f"  Min: {summary['cost_range']['min']:.2f} cents")
            print(f"  Max: {summary['cost_range']['max']:.2f} cents")
            print("="*60)

            logger.info("Backfill completed successfully")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the backfill
    asyncio.run(main())
