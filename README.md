# BullsBears - AI-Powered Directional Trading

```
██████╗ ██╗   ██╗██╗     ██╗     ███████╗██████╗ ███████╗ █████╗ ██████╗ ███████╗
██╔══██╗██║   ██║██║     ██║     ██╔════╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝
██████╔╝██║   ██║██║     ██║     ███████╗██████╔╝█████╗  ███████║██████╔╝███████╗
██╔══██╗██║   ██║██║     ██║     ╚════██║██╔══██╗██╔══╝  ██╔══██║██╔══██╗╚════██║
██████╔╝╚██████╔╝███████╗███████╗███████║██████╔╝███████╗██║  ██║██║  ██║███████║
╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
```

> **⚠️ [WARNING] This is for educational purposes only. Not financial advice.**

A cyberpunk-themed, AI-powered directional trading analysis system that combines neural networks, sentiment analysis, and technical indicators to generate high-confidence directional plays with bull/bear bias controls.

## 🔑 API Key Setup

**IMPORTANT**: For security reasons, API keys must be configured as environment variables. The in-app settings panel has been removed for production security.

### For Local Development

1. Copy the environment template:
```bash
cp backend/.env.example backend/.env
```

2. Edit `backend/.env` and add your API keys:
```bash
# Critical APIs (required for full functionality)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
NEWS_API_KEY=your_news_api_key_here

# Optional APIs (enhance features but not required)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
FINNHUB_API_KEY=your_finnhub_key_here
GROK_API_KEY=your_grok_api_key_here
```

3. Restart the backend server:
```bash
cd backend && python3 -m uvicorn app.main:app --reload
```

4. Check configuration status at: http://localhost:8000/health/config

### For GitHub Deployment

1. Go to your repository: **Settings** → **Secrets and variables** → **Actions**
2. Add each API key as a new repository secret:
   - `ALPHA_VANTAGE_API_KEY`
   - `NEWS_API_KEY`
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `FINNHUB_API_KEY`
   - `GROK_API_KEY`

### API Key Acquisition Guide

#### Critical APIs (Required)

**Alpha Vantage** - Stock data and technical indicators
- Sign up: https://www.alphavantage.co/support/#api-key
- Free tier: 25 requests/day, 5 requests/minute
- Used for: Real-time stock prices, technical analysis

**News API** - Financial news sentiment
- Sign up: https://newsapi.org/register
- Free tier: 1000 requests/month
- Used for: News sentiment analysis, market catalysts

#### Optional APIs (Enhanced Features)

**Reddit API** - Social sentiment analysis
- Setup: https://www.reddit.com/prefs/apps
- Free tier: 60 requests/minute
- Used for: r/wallstreetbets and r/stocks sentiment

**Finnhub** - Options data
- Sign up: https://finnhub.io/register
- Free tier: 60 calls/minute
- Used for: Top 10 most traded options

**Grok AI** - AI recommendation validation
- Sign up: https://console.x.ai/
- Pricing: Pay-per-use
- Used for: AI recommendation validation and analysis

## 🚀 Features

- **🤖 AI Neural Network Analysis**: Advanced algorithms analyze market data using multiple data sources
- **📊 Multi-Source Data Fusion**: Technical indicators, news sentiment, social media, and prediction markets
- **⚡ Real-Time Processing**: Live market data with 30-second refresh intervals
- **🎯 Confidence Scoring**: Weighted analysis with 70%+ confidence threshold
- **🔒 Rate Limiting**: Built-in API protection with daily usage limits
- **🌙 Cyberpunk UI**: Dark 90s coder aesthetic with terminal-style interface
- **🔐 Secure Configuration**: Environment variable-based API key management

## 📋 Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **npm or yarn**
- **API Keys** (see setup section below)

## 🛠️ Quick Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd bullsbears-trading
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env with your API keys (see API Setup section)
nano .env
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install Node.js dependencies
npm install

# Start development server
npm run dev
```

### 4. Start the Backend

```bash
# In backend directory
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 Usage

### 1. Configure Trading Parameters

- **Position Size**: Amount to invest ($100 - $50,000)
- **Confidence Threshold**: Minimum confidence for recommendations (60% - 90%)
- **Timeframe**: Analysis period (1 day - 1 month)
- **Risk Level**: Conservative, Moderate, or Aggressive

### 2. Generate AI Plays

Click **"EXECUTE NEURAL SCAN"** to start the analysis. The system will:

1. Fetch top 10 most traded options from Finnhub
2. Analyze technical indicators using Alpha Vantage
3. Process news sentiment from multiple sources
4. Analyze social media sentiment (Reddit/Twitter)
5. Generate confidence-weighted recommendations

### 3. Review Results

The system displays:
- **Options Chain**: Strike prices, expiration dates, premiums
- **Confidence Score**: AI-calculated probability of success
- **Risk Assessment**: Maximum loss potential and position sizing
- **Analysis Breakdown**: Technical, news, social, and fundamental scores

## ⚡ Rate Limits & Usage

- **Daily Limit**: 5 AI generations per day (resets at midnight EST)
- **API Caching**: 30-second cache for real-time data
- **Fallback System**: Static data when APIs are rate-limited
- **Usage Tracking**: Real-time display of remaining generations

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Required
ALPHA_VANTAGE_API_KEY=your_key
NEWS_API_KEY=your_key

# Optional
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=YourApp/1.0
FINNHUB_API_KEY=your_key
GROK_API_KEY=your_key

# Database
DATABASE_URL=sqlite:///./bullsbears.db

# Security
SECRET_KEY=your_secret_key_here
```

## 🚨 Troubleshooting

**"Database connection failed"**
- Start PostgreSQL: `docker-compose up postgres -d`
- Or install PostgreSQL locally

**"Redis connection failed"**  
- Start Redis: `docker-compose up redis -d`
- Or install Redis locally (app works without Redis)

**"API key invalid"**
- Double-check your API keys in `backend/.env`
- Ensure no extra spaces or quotes

**"No module named 'app'"**
- Run from backend directory: `cd backend`
- Install dependencies: `pip install -r requirements.txt`

## 📈 Performance Notes

- First analysis may take 10-15 seconds (fetching data)
- Subsequent analyses are cached (30 seconds)
- Rate limits respected automatically
- Works during market hours and after-hours

## 🏗️ Architecture

```
bullsbears/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Configuration, database, Redis
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # External API integrations
│   │   └── analyzers/    # Analysis engines
│   ├── tests/            # Test suite
│   └── requirements.txt
├── frontend/             # Next.js frontend (Phase 5)
└── docker-compose.yml    # Development environment
```

## 🔧 Configuration

### Required API Keys

1. **Alpha Vantage** (Primary data source)
   - Get free key: https://www.alphavantage.co/support/#api-key
   - 5 calls/minute, 500 calls/day (free tier)

2. **NewsAPI** (News sentiment)
   - Get free key: https://newsapi.org/register
   - 1000 requests/day (free tier)

3. **Twitter API v2** (Optional - Social sentiment)
   - Apply at: https://developer.twitter.com/
   - Essential access: 500k tweets/month

4. **StockTwits** (Optional - Trader sentiment)
   - Register at: https://api.stocktwits.com/developers

### Environment Variables

See `.env.example` for all configuration options including:
- Database connections
- Redis configuration
- API keys and rate limits
- Caching strategies
- Security settings

## 🧪 Testing

```bash
# Run all tests
cd backend
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_main.py -v
```

## 📈 Performance Requirements

- API endpoints: < 200ms average response time
- WebSocket updates: < 100ms latency
- Database queries: < 50ms average
- Support for 1000+ concurrent users

## 🔒 Security Features

- Rate limiting (100 requests/minute per user)
- CORS configuration
- Input validation and sanitization
- Secure API key management
- No storage of personal trading positions

## 🚀 Deployment

### Production Deployment
```bash
# Build and deploy with Docker
docker-compose -f docker-compose.prod.yml up -d

# Or deploy to cloud platforms
# (AWS, GCP, Azure deployment guides coming soon)
```

### Monitoring
- Application health checks
- Real-time error tracking
- Performance monitoring
- API usage analytics

## 📝 Development Status

**Current Phase: 1 - Core Backend Foundation ✅**

- [x] Project structure and configuration
- [x] FastAPI application with CORS
- [x] Database models (PostgreSQL)
- [x] Redis caching setup
- [x] Docker containerization
- [x] Health monitoring
- [x] Basic testing framework

**Next: Phase 2 - Data Collection Services**

## 🤝 Contributing

This is a personal project, but feel free to:
1. Fork the repository
2. Add your own analysis features
3. Share improvements via pull requests

## 📄 License

MIT License - Use for personal/educational purposes only.

## ⚠️ Risk Warning

Options trading involves substantial risk of loss and is not suitable for all investors. Certain complex options strategies carry additional risk. Before trading options, please read the "Characteristics and Risks of Standardized Options" available from your broker or from The Options Clearing Corporation at https://www.theocc.com/about/publications/character-risks.jsp.
