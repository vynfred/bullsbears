---
type: "always_apply"
---

# Options Trading Web App - Updated Build Rules

## Project Overview
Build a **personal-use** real-time web application that analyzes multiple data sources to provide confidence-rated buy/sell recommendations for stock options trading. Designed for local development and GitHub sharing.

## Architecture Requirements

### Backend (Python/FastAPI) - ✅ COMPLETED
- FastAPI with high-performance async API endpoints
- WebSocket connections for real-time data streaming (Phase 4)
- Redis for caching and session management (optional for development)
- PostgreSQL for storing historical data and user preferences
- Celery for background tasks (Phase 4)

### Frontend (React/Next.js) - 🔄 CURRENT PHASE
- **Manual trigger dashboard** - analysis only runs when user clicks button
- Real-time results display with confidence scoring
- Mobile-responsive design for trading on-the-go
- Dark/light theme toggle
- Interactive options chain visualization

### Data Pipeline - ✅ COMPLETED
- **On-demand data ingestion** when user requests analysis
- Real-time API calls during analysis (30-second caching)
- Comprehensive error handling and data validation
- Rate limiting compliance for all APIs
- Circuit breaker patterns for API failures

## Data Sources Integration - ✅ COMPLETED

### Stock/Options Data
- **Primary**: Alpha Vantage API for real-time quotes and technical indicators
- **Secondary**: Yahoo Finance (yfinance) for backup data and options chains
- **Additional**: Financial Modeling Prep for fundamentals
- Options chain data with Greeks (delta, gamma, theta, vega)
- Volume and open interest tracking

### News Analysis
- NewsAPI for general financial news
- Finnhub for company-specific news and earnings
- Alpha Vantage news sentiment
- SEC filings monitoring (8-K, 10-Q, 10-K)
- Earnings calendar integration

### Social Media Monitoring
- Reddit API for r/wallstreetbets, r/stocks analysis
- **Note**: Twitter/StockTwits APIs too restrictive for free tier
- Implement sentiment scoring (-1 to +1 scale)
- Alternative: Google Trends integration (future enhancement)

### Technical Analysis - ✅ COMPLETED
- TA-Lib for all technical indicators (local processing)
- Required indicators: RSI, MACD, Bollinger Bands, Moving Averages
- Volume analysis and unusual activity detection
- Support/resistance level identification

## Confidence Scoring System - ✅ COMPLETED

### Updated Weighted Scoring Model (Total: 100%)
- **Technical Analysis: 45%** (increased from 35% - most reliable)
- **News Sentiment: 35%** (increased from 25% - high impact)
- **Earnings/Fundamentals: 20%** (increased from 15% - concrete data)
- **Social Media: 0%** (removed due to API limitations)

### Confidence Levels
- 90-100%: STRONG BUY/SELL
- 70-89%: MODERATE BUY/SELL
- 50-69%: WEAK BUY/SELL
- Below 50%: HOLD/NO ACTION

### Risk Assessment - ✅ COMPLETED
- Calculate maximum loss potential
- Time decay impact for options
- Volatility risk assessment
- Position sizing recommendations

## Code Structure Requirements - ✅ COMPLETED

### Project Structure
```
options_trader/
├── backend/                    # ✅ COMPLETED
│   ├── app/
│   │   ├── api/v1/            # REST API endpoints
│   │   ├── core/              # Config, database, Redis
│   │   ├── models/            # SQLAlchemy models
│   │   ├── services/          # External API integrations
│   │   ├── analyzers/         # Analysis engines
│   │   └── main.py           # FastAPI application
│   ├── tests/                 # Unit tests
│   └── requirements.txt       # Dependencies
├── frontend/                   # 🔄 CURRENT PHASE
│   ├── src/
│   │   ├── app/              # Next.js app router
│   │   ├── components/       # React components
│   │   ├── lib/              # API client
│   │   └── types/            # TypeScript interfaces
│   └── package.json
├── docker-compose.yml          # Development environment
├── run_dev.py                 # Simple development runner
└── README.md                  # User setup instructions
```

### Naming Conventions
- Use snake_case for Python files and functions
- Use PascalCase for Python classes
- Use camelCase for JavaScript/TypeScript
- Prefix API endpoints with /api/v1/
- Use descriptive variable names (no abbreviations)

### Error Handling - ✅ IMPLEMENTED
- Comprehensive try-catch blocks with circuit breakers
- Structured logging with context and timestamps
- Graceful degradation when data sources fail
- User-friendly error messages in frontend

## API Integration - ✅ COMPLETED

### Free Tier APIs (Proven Working)
- **Alpha Vantage**: 5 calls/minute, 500/day (primary stock data)
- **NewsAPI**: 1000 requests/month (general news)
- **Finnhub**: 60 calls/minute (company news, earnings)
- **Yahoo Finance**: Unlimited via yfinance (backup data, VIX, indices)
- **FRED**: Unlimited (economic data)
- **Reddit**: Standard rate limits (social sentiment)

### Caching Strategy - ✅ IMPLEMENTED
- Cache API responses for 30 seconds
- Store calculated indicators for 5 minutes
- User preferences cached for 1 hour
- Historical data cached for 24 hours

## Security & Compliance - ✅ IMPLEMENTED

### API Security
- Rate limiting: 100 requests per minute per user
- Input validation and sanitization
- CORS configuration for frontend domain only
- Environment variable management for API keys

### Data Privacy
- **No storage of personal trading positions**
- **No user accounts or personal data collection**
- Anonymized usage analytics only
- Local development focus (no cloud deployment)

## Performance Requirements - ✅ MET

### Response Times
- API endpoints: < 200ms average (achieved)
- Analysis requests: 10-15 seconds first time, cached thereafter
- Database queries: < 50ms average
- Frontend page loads: < 3 seconds

### Scalability
- Designed for personal use (1 user)
- Docker containerization for easy deployment
- Database connection pooling
- Redis caching for performance

## Testing Requirements - 🔄 IN PROGRESS

### Backend Testing
- Unit tests for all analyzer functions (target: 90%+ coverage)
- Integration tests for API endpoints
- Mock external API responses for testing
- Error handling and circuit breaker testing

### Frontend Testing
- Component testing with React Testing Library
- API integration testing
- Mobile responsiveness testing

## Deployment & Monitoring - ✅ CONFIGURED

### Infrastructure
- **Local development focus** with Docker containerization
- GitHub repository for sharing and backup
- Environment separation (development/production)
- Simple deployment with docker-compose

### Monitoring
- Health check endpoints implemented
- Structured logging throughout application
- API usage tracking and rate limit monitoring
- Error tracking and alerting

## Legal Disclaimers - ✅ IMPLEMENTED

### Required Disclaimers
- **"Not financial advice"** prominently displayed
- **"Educational purposes only"** messaging
- Risk warnings for options trading
- Data accuracy limitations notice

### Terms of Service
- Personal use license (MIT)
- No liability for trading decisions
- Data usage transparency
- Open source sharing encouraged

## Updated Development Priorities

### ✅ Phase 1: Core Backend Foundation - COMPLETED
- FastAPI application with async patterns
- PostgreSQL database with SQLAlchemy models
- Redis caching setup
- Configuration management

### ✅ Phase 2: Data Collection & Analysis - COMPLETED
- All analyzer components implemented
- API integrations working (Alpha Vantage, NewsAPI, Finnhub, Reddit)
- Confidence scoring engine operational
- REST API endpoints functional

### 🔄 Phase 3: Frontend Dashboard - CURRENT
- Next.js application setup
- Manual trigger interface (analyze button)
- Results display components
- API client integration
- Responsive design implementation

### 📋 Phase 4: Real-Time Features - PLANNED
- WebSocket implementation for live updates
- Background Celery tasks for data collection
- Push notifications for high-confidence signals
- Connection health monitoring

### 📋 Phase 5: Enhancement & Polish - PLANNED
- Advanced options analysis with Greeks
- Watchlist functionality
- Historical performance tracking
- Export capabilities

## Key Changes from Original Rules

1. **Removed social media weight** from confidence scoring due to API limitations
2. **Increased technical analysis weight** to 45% (most reliable data source)
3. **Manual trigger approach** instead of continuous monitoring
4. **Local development focus** instead of cloud deployment
5. **Personal use emphasis** instead of multi-user platform
6. **Simplified API stack** focusing on proven free tiers
7. **GitHub sharing model** for distribution

## Current Implementation Status

The backend is fully functional with comprehensive analysis capabilities. The next phase focuses on creating a clean, responsive frontend that allows users to manually trigger analysis and view results in an intuitive dashboard format.