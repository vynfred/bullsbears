# Phase 2: Moon/Rug Pattern Recognition Implementation

## Overview

This document describes the implementation of Phase 2 of the BullsBears project, which introduces "When Moon?" and "When Rug?" pattern recognition tools. These tools identify patterns that precede significant stock moves (+20% jumps and -20% drops) within 1-3 trading days.

## Architecture

### Core Components

1. **Backtesting Engine** (`app/analyzers/backtest.py`)
   - Analyzes historical data to identify patterns preceding major moves
   - Uses yfinance for bulk OHLCV data and TA-Lib for technical indicators
   - Implements weighted scoring: 40% technical, 30% sentiment, 20% earnings, 10% social

2. **Moon Analyzer** (`app/analyzers/moon_analyzer.py`)
   - Identifies patterns for potential +20% jumps
   - Focuses on oversold technicals, positive sentiment, volume surges
   - Reuses existing confidence scoring infrastructure

3. **Rug Analyzer** (`app/analyzers/rug_analyzer.py`)
   - Identifies patterns for potential -20% drops
   - Focuses on overbought technicals, negative sentiment, bearish signals
   - Mirrors moon analyzer architecture with inverted logic

4. **Daily Scanning** (`app/tasks/daily_scan.py`)
   - Celery tasks scheduled at 9:30 AM ET
   - Scans ~200 volatile tickers for moon/rug patterns
   - Stores alerts with >70% confidence in database

5. **Self-Training Loop** (`app/tasks/weekly_retrain.py`)
   - Weekly ML model retraining using scikit-learn RandomForest
   - Tracks alert outcomes and improves prediction accuracy
   - Updates model performance metrics

## Database Schema

### Extended AnalysisResult Model

New fields added to support moon/rug alerts:

```sql
-- Alert classification
alert_type: ENUM('MOON', 'RUG', 'GENERAL')
features_json: JSONB  -- Pre-signal features
pattern_confidence: FLOAT  -- Pattern-specific confidence
target_timeframe_days: INTEGER  -- Expected days to move
move_threshold_percent: FLOAT  -- Expected move percentage

-- Outcome tracking for self-training
alert_outcome: ENUM('PENDING', 'SUCCESS', 'FAILURE', 'PARTIAL', 'EXPIRED')
actual_move_percent: FLOAT  -- Actual move that occurred
days_to_move: INTEGER  -- Actual days to move
outcome_timestamp: TIMESTAMP  -- When outcome was determined
outcome_notes: TEXT  -- Additional outcome notes
```

## API Endpoints

### Moon Alerts (`/api/v1/moon_alerts`)

- `GET /` - List moon alerts with filtering
- `GET /latest` - Get latest moon alerts for dashboard
- `POST /analyze` - Analyze specific symbol for moon potential
- `GET /stats` - Get moon alert performance statistics
- `GET /{alert_id}` - Get specific moon alert details

### Rug Alerts (`/api/v1/rug_alerts`)

- `GET /` - List rug alerts with filtering
- `GET /latest` - Get latest rug alerts for dashboard
- `POST /analyze` - Analyze specific symbol for rug potential
- `GET /stats` - Get rug alert performance statistics
- `GET /{alert_id}` - Get specific rug alert details

## Celery Tasks

### Daily Scanning (9:30 AM ET, Monday-Friday)

```python
# Combined scan for efficiency
"daily-moon-rug-scan": {
    "task": "app.tasks.daily_scan.combined_daily_scan",
    "schedule": "30 13 * * 1-5",  # 9:30 AM ET (13:30 UTC)
    "options": {"queue": "scanning"}
}
```

### Weekly Retraining (Sundays, 6:00 AM UTC)

```python
"weekly-model-retrain": {
    "task": "app.tasks.weekly_retrain.weekly_retrain_models",
    "schedule": "0 6 * * 0",
    "options": {"queue": "ml_training"}
}
```

### Daily Outcome Updates (8:00 PM UTC)

```python
"update-alert-outcomes": {
    "task": "app.tasks.weekly_retrain.update_alert_outcomes",
    "schedule": "0 20 * * *",
    "options": {"queue": "ml_training"}
}
```

## Installation & Setup

### 1. Database Migration

Run the migration to add new fields:

```bash
psql -d bullsbears -f backend/migrations/add_moon_rug_fields.sql
```

### 2. Install Dependencies

Ensure these packages are installed:

```bash
pip install yfinance scikit-learn pandas numpy ta-lib
```

### 3. Environment Variables

Add to your `.env` file:

```bash
# ML Model Storage
MODEL_DIR=models

# Existing API keys required for full functionality
ALPHA_VANTAGE_API_KEY=your_key
GROK_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
```

### 4. Start Celery Workers

```bash
# Start scanning worker
celery -A app.core.celery worker -Q scanning --loglevel=info

# Start ML training worker
celery -A app.core.celery worker -Q ml_training --loglevel=info

# Start beat scheduler
celery -A app.core.celery beat --loglevel=info
```

### 5. Test the Implementation

```bash
cd backend
python test_backtest.py
```

## Performance Targets

- **API Response Time**: <200ms average
- **Daily Scan Duration**: <5 minutes for 200 tickers
- **Prediction Accuracy**: >60% success rate
- **Alert Confidence Threshold**: >70% for alert generation

## Monitoring & Metrics

### Key Performance Indicators

1. **Alert Generation Rate**: Alerts per day
2. **Success Rate**: Percentage of successful predictions
3. **False Positive Rate**: Percentage of failed predictions
4. **Average Confidence**: Mean confidence of successful alerts
5. **Response Time**: API endpoint performance

### Logging

All components use structured logging with:
- Alert generation events
- Backtesting results
- Model training metrics
- API request/response times
- Error tracking and debugging

## Integration with Existing System

### Reused Components

- **Dual AI System**: Grok + DeepSeek consensus for sentiment analysis
- **Technical Analyzer**: RSI, MACD, Bollinger Bands calculations
- **Confidence Scorer**: Weighted scoring framework
- **Volume Analyzer**: Volume surge detection
- **Redis Caching**: Performance optimization

### New Components

- **Pattern Recognition**: Historical pattern identification
- **ML Training Pipeline**: Automated model improvement
- **Alert Management**: Outcome tracking and validation
- **Specialized Analyzers**: Moon/rug specific logic

## Security & Compliance

### Legal Disclaimers

All alerts include:
- "Not financial advice" warnings
- "Do your own research (DYOR)" notices
- Risk disclaimers for high-volatility predictions
- Past performance disclaimers

### Data Privacy

- No personal trading history storage
- Aggregate/public data processing only
- API key security via environment variables
- Input sanitization for all user inputs

## Future Enhancements

### Phase 3 Roadmap

1. **Frontend Integration**: React components for moon/rug dashboards
2. **Real-time Notifications**: WebSocket alerts for high-confidence patterns
3. **Advanced ML Models**: Deep learning for pattern recognition
4. **Social Media Integration**: X API for CEO activity tracking
5. **Earnings Calendar**: Finnhub integration for catalyst detection

### Scalability Improvements

1. **Distributed Scanning**: Multiple worker nodes
2. **Advanced Caching**: Pattern result caching
3. **Database Optimization**: Partitioning by date/symbol
4. **API Rate Limiting**: Per-user quotas
5. **Model Versioning**: A/B testing for ML improvements

## Troubleshooting

### Common Issues

1. **No Patterns Found**: Check API keys and rate limits
2. **Slow Scanning**: Reduce batch size or add delays
3. **Model Training Fails**: Ensure sufficient historical data
4. **Database Errors**: Run migration script
5. **Celery Tasks Not Running**: Check Redis connection and queues

### Debug Commands

```bash
# Test backtesting engine
python backend/test_backtest.py

# Check Celery status
celery -A app.core.celery inspect active

# Monitor Redis
redis-cli monitor

# Check database
psql -d bullsbears -c "SELECT COUNT(*) FROM analysis_results WHERE alert_type != 'GENERAL';"
```

## Support

For issues or questions:
1. Check logs in `backend/logs/`
2. Review API documentation at `/docs`
3. Test individual components with provided scripts
4. Monitor Celery task status and Redis connections
