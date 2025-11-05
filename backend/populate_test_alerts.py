#!/usr/bin/env python3
"""
Populate test moon/rug alerts for frontend testing
"""
import sqlite3
import json
from datetime import datetime, timedelta
import random

def populate_test_alerts():
    """Add sample moon and rug alerts to the database"""
    
    # Connect to database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Sample stock symbols for testing
    moon_stocks = [
        ('TSLA', 'Tesla Inc'),
        ('NVDA', 'NVIDIA Corporation'),
        ('AAPL', 'Apple Inc'),
        ('MSFT', 'Microsoft Corporation'),
        ('GOOGL', 'Alphabet Inc'),
    ]
    
    rug_stocks = [
        ('HOOD', 'Robinhood Markets Inc'),
        ('COIN', 'Coinbase Global Inc'),
        ('PLTR', 'Palantir Technologies Inc'),
        ('RIVN', 'Rivian Automotive Inc'),
        ('NKLA', 'Nikola Corporation'),
    ]
    
    # Insert sample moon alerts
    print("🌙 Adding moon alerts...")
    for i, (symbol, company) in enumerate(moon_stocks):
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 24))
        confidence = random.uniform(55, 85)
        
        features = {
            'reasons': [
                f'RSI oversold at {random.randint(25, 35)}',
                f'Volume surge {random.uniform(1.5, 3.0):.1f}x average',
                'Positive earnings sentiment',
                'Technical breakout pattern'
            ],
            'target_timeframe': '1-3 days',
            'risk_factors': ['Market volatility', 'Sector rotation risk']
        }
        
        cursor.execute("""
            INSERT INTO analysis_results (
                stock_id, symbol, analysis_type, timestamp, alert_type,
                recommendation, confidence_score, technical_score, 
                news_sentiment_score, social_sentiment_score, earnings_score,
                market_trend_score, pattern_confidence, features_json,
                target_timeframe_days, move_threshold_percent, alert_outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            i + 1, symbol, 'MOON_PATTERN', timestamp, 'MOON',
            'BUY', confidence, random.uniform(70, 90),
            random.uniform(60, 80), random.uniform(55, 75), random.uniform(65, 85),
            random.uniform(60, 80), confidence, json.dumps(features),
            random.randint(1, 3), 20.0, 'PENDING'
        ))
    
    # Insert sample rug alerts
    print("📉 Adding rug alerts...")
    for i, (symbol, company) in enumerate(rug_stocks):
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 24))
        confidence = random.uniform(60, 80)
        
        features = {
            'reasons': [
                f'RSI overbought at {random.randint(70, 85)}',
                'Negative sentiment trend',
                'Insider selling activity',
                'Technical breakdown pattern'
            ],
            'target_timeframe': '1-3 days',
            'risk_factors': ['Market support levels', 'Earnings catalyst risk']
        }
        
        cursor.execute("""
            INSERT INTO analysis_results (
                stock_id, symbol, analysis_type, timestamp, alert_type,
                recommendation, confidence_score, technical_score, 
                news_sentiment_score, social_sentiment_score, earnings_score,
                market_trend_score, pattern_confidence, features_json,
                target_timeframe_days, move_threshold_percent, alert_outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            i + 100, symbol, 'RUG_PATTERN', timestamp, 'RUG',
            'SELL', confidence, random.uniform(30, 50),
            random.uniform(20, 40), random.uniform(25, 45), random.uniform(35, 55),
            random.uniform(40, 60), confidence, json.dumps(features),
            random.randint(1, 3), -20.0, 'PENDING'
        ))
    
    # Commit changes
    conn.commit()
    
    # Verify data was inserted
    cursor.execute("SELECT COUNT(*) FROM analysis_results WHERE alert_type = 'MOON'")
    moon_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analysis_results WHERE alert_type = 'RUG'")
    rug_count = cursor.fetchone()[0]
    
    print(f"✅ Added {moon_count} moon alerts and {rug_count} rug alerts")
    
    # Show sample data
    cursor.execute("""
        SELECT symbol, alert_type, confidence_score, timestamp 
        FROM analysis_results 
        WHERE alert_type IN ('MOON', 'RUG') 
        ORDER BY timestamp DESC 
        LIMIT 5
    """)
    
    print("\n📊 Sample alerts:")
    for row in cursor.fetchall():
        symbol, alert_type, confidence, timestamp = row
        print(f"  {symbol}: {alert_type} ({confidence:.1f}% confidence) - {timestamp}")
    
    conn.close()
    print("\n🎉 Test data populated successfully!")

if __name__ == "__main__":
    populate_test_alerts()
