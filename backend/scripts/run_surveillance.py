#!/usr/bin/env python3
"""
NASDAQ Rolling Surveillance System Runner
Process weekly batches of 1,000 stocks with comprehensive market intelligence
"""

import asyncio
import asyncpg
import aiohttp
import logging
import argparse
from datetime import datetime, timezone
import os
import json
import random
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SurveillanceRunner:
    """Main surveillance system runner"""
    
    def __init__(self, week_number: int = 1):
        self.week_number = week_number
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://vynfred@localhost:5432/bullsbears')
        self.fmp_api_key = os.getenv('FMP_API_KEY')
        self.base_url = "https://financialmodelingprep.com/api/v3"
        
        # API rate limiting (FMP Premium: 300 calls/minute)
        self.max_calls_per_minute = 300
        self.call_delay = 60 / self.max_calls_per_minute  # ~0.2 seconds between calls
        
        # Session and connection objects
        self.session = None
        self.conn = None
        
        # Tracking
        self.api_calls_made = 0
        self.successful_scans = 0
        self.failed_scans = 0
        self.alerts_generated = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        self.conn = await asyncpg.connect(self.db_url)
        logger.info("✅ Connected to database and HTTP session")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.conn:
            await self.conn.close()
        logger.info("✅ Closed database and HTTP connections")
    
    async def get_weekly_batch(self) -> List[str]:
        """Get symbols for this week's surveillance batch"""
        try:
            # Get symbols with deterministic randomization
            query = """
                SELECT symbol FROM nasdaq_symbols 
                WHERE is_active = true 
                ORDER BY symbol
            """
            
            symbols = await self.conn.fetch(query)
            symbol_list = [row['symbol'] for row in symbols]
            
            # Deterministic randomization based on week number
            random.seed(self.week_number * 42)
            shuffled_symbols = random.sample(symbol_list, len(symbol_list))
            
            # Get this week's batch (100 stocks for comprehensive test)
            batch_size = 100  # Comprehensive test batch
            start_idx = (self.week_number - 1) * batch_size
            end_idx = min(start_idx + batch_size, len(shuffled_symbols))

            weekly_batch = shuffled_symbols[start_idx:end_idx]
            
            logger.info(f"📦 Week {self.week_number} batch: {len(weekly_batch)} symbols")
            logger.info(f"📊 Range: {start_idx+1} to {end_idx} of {len(shuffled_symbols)} total")
            
            return weekly_batch
            
        except Exception as e:
            logger.error(f"❌ Error getting weekly batch: {e}")
            return []
    
    async def fetch_with_rate_limit(self, url: str) -> Optional[Dict]:
        """Fetch data with rate limiting"""
        try:
            # Rate limiting delay
            await asyncio.sleep(self.call_delay)
            
            async with self.session.get(url) as response:
                self.api_calls_made += 1
                
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 429:  # Rate limited
                    logger.warning("⚠️ Rate limited, waiting 60 seconds...")
                    await asyncio.sleep(60)
                    return await self.fetch_with_rate_limit(url)  # Retry
                else:
                    logger.warning(f"⚠️ API error {response.status} for URL: {url}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Fetch error for {url}: {e}")
            return None
    
    async def collect_stock_data(self, symbol: str) -> Optional[Dict]:
        """Collect comprehensive data for a single stock"""
        try:
            logger.info(f"🔍 Scanning {symbol}...")
            
            # Collect multiple data points efficiently
            data_points = {}
            
            # 1. Quote data (price, volume, etc.)
            quote_url = f"{self.base_url}/quote/{symbol}?apikey={self.fmp_api_key}"
            quote_data = await self.fetch_with_rate_limit(quote_url)
            if quote_data and len(quote_data) > 0:
                data_points['quote'] = quote_data[0]
            
            # 2. Company profile (market cap, sector, etc.)
            profile_url = f"{self.base_url}/profile/{symbol}?apikey={self.fmp_api_key}"
            profile_data = await self.fetch_with_rate_limit(profile_url)
            if profile_data and len(profile_data) > 0:
                data_points['profile'] = profile_data[0]
            
            # 3. Key metrics (PE ratio, debt/equity, etc.)
            metrics_url = f"{self.base_url}/key-metrics/{symbol}?apikey={self.fmp_api_key}"
            metrics_data = await self.fetch_with_rate_limit(metrics_url)
            if metrics_data and len(metrics_data) > 0:
                data_points['metrics'] = metrics_data[0]
            
            # 4. Institutional holders
            institutional_url = f"{self.base_url}/institutional-holder/{symbol}?apikey={self.fmp_api_key}"
            institutional_data = await self.fetch_with_rate_limit(institutional_url)
            if institutional_data:
                data_points['institutional'] = institutional_data
            
            # 5. Insider trading (last 30 days)
            insider_url = f"{self.base_url}/insider-trading?symbol={symbol}&apikey={self.fmp_api_key}"
            insider_data = await self.fetch_with_rate_limit(insider_url)
            if insider_data:
                data_points['insider'] = insider_data
            
            # 6. Technical indicators (RSI)
            rsi_url = f"{self.base_url}/technical_indicator/1day/{symbol}?period=14&type=rsi&apikey={self.fmp_api_key}"
            rsi_data = await self.fetch_with_rate_limit(rsi_url)
            if rsi_data and len(rsi_data) > 0:
                data_points['rsi'] = rsi_data[0]
            
            # 7. Recent news
            news_url = f"{self.base_url}/stock_news?tickers={symbol}&limit=10&apikey={self.fmp_api_key}"
            news_data = await self.fetch_with_rate_limit(news_url)
            if news_data:
                data_points['news'] = news_data
            
            # Calculate data completeness
            expected_data_points = 7
            actual_data_points = len(data_points)
            data_completeness = actual_data_points / expected_data_points
            
            logger.info(f"✅ {symbol}: {actual_data_points}/{expected_data_points} data points collected")
            
            return {
                'symbol': symbol,
                'data_points': data_points,
                'data_completeness': data_completeness,
                'api_calls_used': 7  # We made 7 API calls for this stock
            }
            
        except Exception as e:
            logger.error(f"❌ Error collecting data for {symbol}: {e}")
            return None
    
    def analyze_stock_data(self, stock_data: Dict) -> Dict:
        """Analyze collected data and detect significant changes"""
        symbol = stock_data['symbol']
        data_points = stock_data['data_points']
        
        # Initialize analysis results
        analysis = {
            'symbol': symbol,
            'scan_date': datetime.now(timezone.utc),
            'week_number': self.week_number,
            'change_flags': [],
            'significance_score': 0.0,
            'data_completeness': stock_data['data_completeness'],
            'api_calls_used': stock_data['api_calls_used']
        }
        
        # Extract key metrics
        quote = data_points.get('quote', {})
        profile = data_points.get('profile', {})
        metrics = data_points.get('metrics', {})
        institutional = data_points.get('institutional', [])
        insider = data_points.get('insider', [])
        rsi_data = data_points.get('rsi', {})
        news = data_points.get('news', [])
        
        # Basic market data
        analysis.update({
            'current_price': float(quote.get('price', 0)),
            'volume': int(quote.get('volume', 0)),
            'market_cap': int(profile.get('mktCap', 0)),
            'avg_volume': int(quote.get('avgVolume', 1)),
        })
        
        # Technical indicators
        analysis.update({
            'rsi': float(rsi_data.get('rsi', 50)),
            'volume_ratio': analysis['volume'] / analysis['avg_volume'] if analysis['avg_volume'] > 0 else 1.0,
            'day_high': float(quote.get('dayHigh', 0)),
            'day_low': float(quote.get('dayLow', 0)),
        })
        
        # Fundamental data
        analysis.update({
            'pe_ratio': float(metrics.get('peRatio', 0)) if metrics.get('peRatio') else None,
            'debt_to_equity': float(metrics.get('debtToEquity', 0)) if metrics.get('debtToEquity') else None,
            'revenue_growth': float(metrics.get('revenueGrowth', 0)) if metrics.get('revenueGrowth') else None,
        })
        
        # Institutional data
        institutional_ownership = sum(holder.get('sharesNumber', 0) for holder in institutional) / 1_000_000 if institutional else 0
        analysis.update({
            'institutional_ownership': min(institutional_ownership, 100.0),
            'institutional_flow_change': 0.0,  # Will be calculated against previous scan
        })
        
        # Insider trading analysis
        recent_insider_buys = [t for t in insider if t.get('transactionType') == 'P-Purchase']
        recent_insider_sells = [t for t in insider if t.get('transactionType') == 'S-Sale']
        
        analysis.update({
            'insider_buy_count': len(recent_insider_buys),
            'insider_sell_count': len(recent_insider_sells),
            'insider_net_value': sum(t.get('securitiesTransacted', 0) * t.get('price', 0) for t in recent_insider_buys) - 
                               sum(t.get('securitiesTransacted', 0) * t.get('price', 0) for t in recent_insider_sells),
        })
        
        # News sentiment (simplified)
        analysis.update({
            'sentiment_score': self.calculate_news_sentiment(news),
            'news_count': len(news),
        })
        
        # Detect significant changes
        change_flags = []
        significance_score = 0.0
        
        # Volume surge detection
        if analysis['volume_ratio'] > 3.0:
            change_flags.append('VOLUME_SURGE')
            significance_score += 0.3
        
        # RSI extremes
        if analysis['rsi'] < 30:
            change_flags.append('OVERSOLD')
            significance_score += 0.2
        elif analysis['rsi'] > 70:
            change_flags.append('OVERBOUGHT')
            significance_score += 0.15
        
        # Insider accumulation
        if analysis['insider_buy_count'] >= 2:
            change_flags.append('INSIDER_ACCUMULATION')
            significance_score += 0.25
        
        # High news activity
        if analysis['news_count'] > 5:
            change_flags.append('HIGH_NEWS_ACTIVITY')
            significance_score += 0.1
        
        # Market cap weighting
        if analysis['market_cap'] > 10_000_000_000:  # $10B+
            significance_score *= 1.1
        elif analysis['market_cap'] > 1_000_000_000:  # $1B+
            significance_score *= 1.05
        
        analysis['change_flags'] = change_flags
        analysis['significance_score'] = min(significance_score, 1.0)
        
        return analysis
    
    def calculate_news_sentiment(self, news_data: List[Dict]) -> float:
        """Calculate sentiment score from news (simplified)"""
        if not news_data:
            return 0.5  # Neutral
        
        positive_keywords = ['growth', 'profit', 'beat', 'strong', 'bullish', 'upgrade', 'buy']
        negative_keywords = ['loss', 'decline', 'weak', 'bearish', 'downgrade', 'sell', 'miss']
        
        sentiment_scores = []
        for article in news_data:
            title = article.get('title', '').lower()
            text = article.get('text', '').lower()
            content = f"{title} {text}"
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in content)
            negative_count = sum(1 for keyword in negative_keywords if keyword in content)
            
            if positive_count + negative_count > 0:
                score = positive_count / (positive_count + negative_count)
                sentiment_scores.append(score)
        
        return sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5
    
    async def store_surveillance_record(self, analysis: Dict) -> bool:
        """Store surveillance analysis in database"""
        try:
            insert_query = """
                INSERT INTO stock_surveillance (
                    symbol, scan_date, week_number, current_price, volume, market_cap, avg_volume,
                    rsi, volume_ratio, day_high, day_low, pe_ratio, debt_to_equity, revenue_growth,
                    institutional_ownership, institutional_flow_change, insider_buy_count, 
                    insider_sell_count, insider_net_value, sentiment_score, news_count,
                    change_flags, significance_score, data_completeness, api_calls_used
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
                )
            """
            
            await self.conn.execute(
                insert_query,
                analysis['symbol'], analysis['scan_date'], analysis['week_number'],
                analysis['current_price'], analysis['volume'], analysis['market_cap'], analysis['avg_volume'],
                analysis['rsi'], analysis['volume_ratio'], analysis['day_high'], analysis['day_low'],
                analysis['pe_ratio'], analysis['debt_to_equity'], analysis['revenue_growth'],
                analysis['institutional_ownership'], analysis['institutional_flow_change'],
                analysis['insider_buy_count'], analysis['insider_sell_count'], analysis['insider_net_value'],
                analysis['sentiment_score'], analysis['news_count'],
                json.dumps(analysis['change_flags']), analysis['significance_score'],
                analysis['data_completeness'], analysis['api_calls_used']
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing surveillance record for {analysis['symbol']}: {e}")
            return False
    
    async def generate_alert_if_significant(self, analysis: Dict) -> bool:
        """Generate alert if stock shows significant patterns"""
        if analysis['significance_score'] < 0.5:  # Only high-significance stocks
            return False
        
        try:
            # Determine alert type
            alert_type = 'breakout_potential'
            if 'OVERSOLD' in analysis['change_flags']:
                alert_type = 'oversold_bounce'
            elif 'INSIDER_ACCUMULATION' in analysis['change_flags']:
                alert_type = 'insider_accumulation'
            elif 'VOLUME_SURGE' in analysis['change_flags']:
                alert_type = 'volume_breakout'
            
            # Create alert message
            message = f"{analysis['symbol']} surveillance alert: {', '.join(analysis['change_flags'])}"
            
            # Estimate target price (simplified)
            target_estimate = analysis['current_price'] * (1 + analysis['significance_score'] * 0.2)  # Up to 20% upside
            
            # Insert alert
            alert_query = """
                INSERT INTO surveillance_alerts (
                    symbol, alert_type, confidence, trigger_factors, current_price, 
                    target_estimate, message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await self.conn.execute(
                alert_query,
                analysis['symbol'], alert_type, analysis['significance_score'],
                json.dumps(analysis['change_flags']), analysis['current_price'],
                target_estimate, message
            )
            
            self.alerts_generated += 1
            logger.info(f"🚨 ALERT: {message} (Confidence: {analysis['significance_score']:.2f})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating alert for {analysis['symbol']}: {e}")
            return False
    
    async def update_batch_status(self, status: str, **kwargs):
        """Update surveillance batch status"""
        try:
            update_query = """
                UPDATE surveillance_batches 
                SET status = $1, processed_symbols = $2, failed_symbols = $3, 
                    alerts_generated = $4, total_api_calls = $5, processing_time_minutes = $6,
                    completed_at = CASE WHEN $1 = 'completed' THEN NOW() ELSE completed_at END
                WHERE week_number = $7
            """
            
            processing_time = kwargs.get('processing_time_minutes', 0)
            
            await self.conn.execute(
                update_query, status, self.successful_scans, self.failed_scans,
                self.alerts_generated, self.api_calls_made, processing_time, self.week_number
            )
            
        except Exception as e:
            logger.error(f"❌ Error updating batch status: {e}")
    
    async def run_weekly_surveillance(self):
        """Run surveillance for the specified week"""
        start_time = datetime.now()
        logger.info(f"🚀 Starting Week {self.week_number} NASDAQ Surveillance")
        logger.info("=" * 60)
        
        try:
            # Update batch status to in_progress
            await self.update_batch_status('in_progress')
            
            # Get weekly batch
            weekly_batch = await self.get_weekly_batch()
            if not weekly_batch:
                logger.error("❌ No symbols to process")
                return False
            
            logger.info(f"📦 Processing {len(weekly_batch)} symbols...")
            
            # Process each symbol
            for i, symbol in enumerate(weekly_batch, 1):
                try:
                    # Collect data
                    stock_data = await self.collect_stock_data(symbol)
                    if not stock_data:
                        self.failed_scans += 1
                        continue
                    
                    # Analyze data
                    analysis = self.analyze_stock_data(stock_data)
                    
                    # Store surveillance record
                    if await self.store_surveillance_record(analysis):
                        self.successful_scans += 1
                        
                        # Generate alert if significant
                        await self.generate_alert_if_significant(analysis)
                    else:
                        self.failed_scans += 1
                    
                    # Progress update
                    if i % 50 == 0:
                        progress = (i / len(weekly_batch)) * 100
                        logger.info(f"📊 Progress: {i}/{len(weekly_batch)} ({progress:.1f}%) - "
                                  f"API calls: {self.api_calls_made}, Alerts: {self.alerts_generated}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {symbol}: {e}")
                    self.failed_scans += 1
            
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds() / 60
            
            # Update batch status to completed
            await self.update_batch_status('completed', processing_time_minutes=int(processing_time))
            
            # Final summary
            logger.info("=" * 60)
            logger.info(f"✅ Week {self.week_number} Surveillance Complete!")
            logger.info(f"📊 Processed: {self.successful_scans}/{len(weekly_batch)} symbols")
            logger.info(f"❌ Failed: {self.failed_scans} symbols")
            logger.info(f"🚨 Alerts generated: {self.alerts_generated}")
            logger.info(f"📞 API calls made: {self.api_calls_made}")
            logger.info(f"⏱️ Processing time: {processing_time:.1f} minutes")
            logger.info(f"⚡ Rate: {len(weekly_batch)/processing_time:.1f} stocks/minute")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Surveillance failed: {e}")
            await self.update_batch_status('failed')
            return False

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run NASDAQ Rolling Surveillance')
    parser.add_argument('--week', type=int, default=1, help='Week number to process (default: 1)')
    args = parser.parse_args()
    
    async with SurveillanceRunner(args.week) as runner:
        success = await runner.run_weekly_surveillance()
        
        if success:
            print(f"\n🎉 Week {args.week} surveillance completed successfully!")
            print("📊 Check surveillance_alerts table for new opportunities")
            print("📈 Review high_priority_stocks view for significant patterns")
        else:
            print(f"\n❌ Week {args.week} surveillance failed")

if __name__ == "__main__":
    asyncio.run(main())
