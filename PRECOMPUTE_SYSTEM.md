# BullsBears.xyz Pre-Computed Analysis System

## Overview

The pre-computed analysis system transforms BullsBears.xyz from a real-time API-per-request architecture to a scalable, quota-efficient platform that can handle 1000+ users without hitting rate limits.

## Architecture

### Multi-Tier Fallback System

1. **Redis Cache** (Tier 1) - 5-30 minutes fresh
   - Instant response times (<100ms)
   - Highest priority data source
   - Automatic cache hit rate tracking

2. **Database Precomputed** (Tier 2) - 1+ hours fresh
   - Fast database queries (<200ms)
   - Comprehensive analysis storage
   - Metadata tracking for freshness

3. **Real-Time API** (Tier 3) - Rate limited to 5/day
   - Fallback for non-precomputed stocks
   - Automatic background update triggering
   - Exponential backoff for API failures

4. **Stale Data + Warnings** (Tier 4) - Always available
   - Graceful degradation when APIs fail
   - Clear staleness indicators
   - User education about data age

## Key Features

### Smart Caching
- TTL-aware caching with metadata
- Cache hit rate monitoring
- Automatic cache invalidation
- Pattern-based cache cleanup

### Background Jobs (Celery)
- Market hours: Every 1 hour (9:30 AM - 4:00 PM ET)
- After hours: Every 2 hours
- Weekend: Every 4 hours
- Daily news updates
- Automatic retry with exponential backoff

### Rate Limiting
- 5 real-time requests per day (free tier)
- IP-based tracking with Redis
- Circuit breaker for API failures
- Graceful degradation to cached data

### Monitoring & Health Checks
- Cache performance metrics
- Job status tracking
- System health endpoints
- Error logging and alerting

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Precompute System
PRECOMPUTE_ENABLED=true
PRECOMPUTE_TOP_STOCKS_COUNT=10
PRECOMPUTE_MARKET_HOURS_INTERVAL=3600
PRECOMPUTE_AFTER_HOURS_INTERVAL=7200
PRECOMPUTE_WEEKEND_INTERVAL=14400

# Rate Limiting
REALTIME_REQUESTS_PER_DAY=5
REALTIME_API_CALLS_PER_REQUEST=2

# Cache TTL (seconds)
CACHE_PRECOMPUTED_ANALYSIS=1800
CACHE_PRECOMPUTED_TECHNICAL=3600
CACHE_PRECOMPUTED_SENTIMENT=1800
CACHE_PRECOMPUTED_NEWS=86400
CACHE_STALE_DATA_WARNING=7200
```

### Top 10 Stocks (Testing Phase)

Currently precomputing analysis for:
- AAPL, MSFT, GOOGL, AMZN, TSLA
- NVDA, META, NFLX, AMD, BABA

## Installation & Setup

### 1. Database Migration

```bash
cd backend
python migrate_precompute.py
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- FastAPI backend
- Celery worker
- Celery beat scheduler
- Flower monitoring (http://localhost:5555)

### 3. Verify Installation

Check system status:
```bash
curl http://localhost:8000/api/v1/precompute/status
```

Check cache performance:
```bash
curl http://localhost:8000/api/v1/cache/stats
```

## API Endpoints

### Analysis with Precompute

```bash
# Use precomputed analysis (default)
GET /api/v1/analyze/AAPL

# Force real-time analysis
GET /api/v1/analyze/AAPL?use_precompute=false

# Response includes data source and freshness info
{
  "success": true,
  "data": { ... },
  "metadata": {
    "data_source": "redis_cache",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Cache Management

```bash
# Get cache statistics
GET /api/v1/cache/stats

# Invalidate cache for symbol
POST /api/v1/cache/invalidate/AAPL
```

### Precompute System

```bash
# Get system status
GET /api/v1/precompute/status

# Manually trigger update
POST /api/v1/precompute/trigger/AAPL
```

## Performance Targets

### Testing Phase Metrics
- **Cache Hit Rate**: >80% for top 10 stocks
- **Response Time**: <100ms for cached data, <2s for real-time
- **API Call Reduction**: 90%+ reduction in external calls
- **Uptime**: 99%+ availability even during API outages

### Load Testing
- 100 concurrent users analyzing top 10 stocks
- API failure simulation with graceful degradation
- Cache performance monitoring
- Background job reliability tracking

## Monitoring

### Health Checks

```bash
# Basic health
GET /health

# Detailed health with precompute status
GET /health/detailed
```

### Celery Monitoring

Access Flower dashboard at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Queue lengths

### Cache Metrics

Monitor cache performance:
- Hit/miss rates by day
- Response time percentiles
- Memory usage
- Key expiration patterns

## Troubleshooting

### Common Issues

1. **Precompute jobs failing**
   - Check Celery worker logs
   - Verify API keys are valid
   - Check rate limits on external APIs

2. **Cache misses too high**
   - Verify Redis connection
   - Check TTL settings
   - Monitor memory usage

3. **Real-time requests blocked**
   - Check rate limiting counters
   - Verify IP-based tracking
   - Review daily limits

### Debug Commands

```bash
# Check Celery worker status
docker logs options_trader_celery

# Check Redis connection
docker exec -it options_trader_redis redis-cli ping

# Check database tables
docker exec -it options_trader_db psql -U postgres -d options_trader -c "\dt"
```

## Scaling Plan

### Phase 1: Testing (Current)
- Top 10 stocks
- 1-hour market hours updates
- Basic monitoring

### Phase 2: Limited Production
- Top 50 stocks
- 30-minute market hours updates
- Enhanced monitoring

### Phase 3: Full Production
- 100+ stocks
- 15-minute market hours updates
- Premium tier features

### Phase 4: Enterprise
- Custom stock lists
- Real-time WebSocket updates
- Advanced analytics

## Security Considerations

- Rate limiting by IP address
- Input validation and sanitization
- Secure API key management
- Database query optimization
- Redis memory limits

## Contributing

When adding new features:
1. Update cache TTL settings appropriately
2. Add monitoring for new endpoints
3. Include error handling and fallbacks
4. Update documentation and tests
5. Consider impact on API quotas
