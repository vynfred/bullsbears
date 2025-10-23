---
type: "always_apply"
---

# Options Trading Web App - Augment Build Rules

## Project Overview
Build a real-time web application that analyzes multiple data sources to provide confidence-rated buy/sell recommendations for stock options trading.

## Architecture Requirements

### Backend (Python/FastAPI)
- Use FastAPI for high-performance async API endpoints
- Implement WebSocket connections for real-time data streaming
- Use Redis for caching and session management
- PostgreSQL for storing historical data and user preferences
- Celery for background tasks (data collection, analysis)

### Frontend (React/Next.js)
- Real-time dashboard with live updating charts
- Mobile-responsive design for trading on-the-go
- Dark/light theme toggle
- Interactive options chain visualization

### Data Pipeline
- Real-time data ingestion every 30 seconds during market hours
- Batch processing for historical analysis overnight
- Error handling and data validation at every step
- Rate limiting compliance for all APIs

## Data Sources Integration

### Stock/Options Data
- Primary: Alpha Vantage API for real-time quotes
- Secondary: Yahoo Finance (yfinance) for backup data
- Options chain data with Greeks (delta, gamma, theta, vega)
- Volume and open interest tracking

### News Analysis
- NewsAPI for general financial news
- Alpha Vantage news sentiment
- SEC filings monitoring (8-K, 10-Q, 10-K)
- Earnings calendar integration

### Social Media Monitoring
- Twitter API v2 for $TICKER mentions and sentiment
- Reddit API for r/wallstreetbets, r/stocks analysis
- StockTwits API for trader sentiment
- Implement sentiment scoring (-1 to +1 scale)

### Technical Analysis
- Use TA-Lib for all technical indicators
- Required indicators: RSI, MACD, Bollinger Bands, Moving Averages
- Volume analysis and unusual activity detection
- Support/resistance level identification

## Confidence Scoring System

### Weighted Scoring Model (Total: 100%)
- Technical Analysis: 35%
- News Sentiment: 25%
- Social Media Sentiment: 20%
- Earnings/Fundamentals: 15%
- Market Trends: 5%

### Confidence Levels
- 90-100%: STRONG BUY/SELL
- 70-89%: MODERATE BUY/SELL
- 50-69%: WEAK BUY/SELL
- Below 50%: HOLD/NO ACTION

### Risk Assessment
- Calculate maximum loss potential
- Time decay impact for options
- Volatility risk assessment
- Position sizing recommendations

## Code Structure Requirements

### Project Structure
```
options_trader/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── analyzers/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   └── package.json
└── docker-compose.yml
```

### Naming Conventions
- Use snake_case for Python files and functions
- Use PascalCase for Python classes
- Use camelCase for JavaScript/TypeScript
- Prefix API endpoints with /api/v1/
- Use descriptive variable names (no abbreviations)

### Error Handling
- Implement comprehensive try-catch blocks
- Log all errors with context and timestamps
- Graceful degradation when data sources fail
- User-friendly error messages in frontend

## Real-Time Features

### WebSocket Implementation
- Live price updates every second during market hours
- Real-time confidence score updates
- Push notifications for high-confidence signals
- Connection health monitoring and auto-reconnect

### Caching Strategy
- Cache API responses for 30 seconds
- Store calculated indicators for 5 minutes
- User preferences cached for 1 hour
- Historical data cached for 24 hours

## Security & Compliance

### API Security
- Rate limiting: 100 requests per minute per user
- API key rotation every 30 days
- Input validation and sanitization
- CORS configuration for frontend domain only

### Data Privacy
- No storage of personal trading positions
- Anonymized usage analytics only
- GDPR compliance for EU users
- Secure environment variable management

## Performance Requirements

### Response Times
- API endpoints: < 200ms average
- WebSocket updates: < 100ms latency
- Page load times: < 3 seconds
- Database queries: < 50ms average

### Scalability
- Support 1000+ concurrent users
- Horizontal scaling capability
- Database connection pooling
- CDN integration for static assets

## Testing Requirements

### Backend Testing
- Unit tests for all analyzer functions (90%+ coverage)
- Integration tests for API endpoints
- Load testing for concurrent users
- Mock external API responses for testing

### Frontend Testing
- Component testing with React Testing Library
- E2E testing with Playwright
- Visual regression testing
- Mobile responsiveness testing

## Deployment & Monitoring

### Infrastructure
- Docker containerization
- AWS/GCP deployment with auto-scaling
- CI/CD pipeline with GitHub Actions
- Environment separation (dev/staging/prod)

### Monitoring
- Application performance monitoring (APM)
- Real-time error tracking
- API usage analytics
- System health dashboards

## Legal Disclaimers

### Required Disclaimers
- "Not financial advice" prominently displayed
- Risk warnings for options trading
- Past performance disclaimers
- Data accuracy limitations notice

### Terms of Service
- User agreement for analysis tool usage
- Limitation of liability clauses
- Data usage and privacy policy
- Account termination conditions