# Options Trading Dashboard

A Next.js frontend dashboard that connects to the FastAPI backend for comprehensive options trading analysis.

## Features

- **Simple Interface**: Clean input field for stock symbols with "Analyze Options" button
- **Real-time Analysis**: Displays confidence scores, technical analysis, and sentiment breakdown
- **Options Chain**: Shows options data with Greeks when confidence score > 70%
- **Backend Health Monitoring**: Visual indicator of backend connection status
- **Responsive Design**: Works on desktop and mobile devices

## Getting Started

### Prerequisites

- Node.js 18+ installed
- FastAPI backend running on http://localhost:8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

### Analyzing a Stock

1. **Enter Stock Symbol**: Type a stock symbol (e.g., AAPL, MSFT) in the input field
2. **Optional Company Name**: Add company name for better news analysis
3. **Click "Analyze Options"**: The system will fetch comprehensive analysis
4. **View Results**: See confidence scores, technical indicators, and sentiment analysis

### Understanding the Results

#### Analysis Components

- **Technical Analysis (35% weight)**: RSI, MACD, Bollinger Bands, Moving Averages
- **News Sentiment (25% weight)**: Analysis of recent news articles
- **Social Media Sentiment (20% weight)**: Twitter, Reddit, StockTwits sentiment
- **Risk Assessment**: Position sizing, stop loss, take profit recommendations

#### Confidence Levels

- **HIGH (90-100%)**: Strong buy/sell signals
- **MEDIUM (70-89%)**: Moderate confidence
- **LOW (50-69%)**: Weak signals

#### Options Chain Display

Options data is automatically displayed when:
- Confidence score ≥ 70%
- Options data is available for the symbol
- Backend successfully retrieves options information

### Popular Symbols

Quick access buttons for commonly analyzed stocks:
- AAPL (Apple), MSFT (Microsoft), GOOGL (Google), AMZN (Amazon)
- TSLA (Tesla), NVDA (NVIDIA), META (Meta), NFLX (Netflix)

## Components

### StockAnalyzer
Input form with stock symbol entry, popular symbols, loading states and error handling.

### AnalysisResults
Comprehensive display of analysis results, technical indicators, risk assessment metrics.

### OptionsChain
Options tables, Greeks calculations, unusual activity alerts, strategy recommendations.

## API Integration

Connects to FastAPI backend at `http://localhost:8000`:
- `GET /api/v1/analyze/{symbol}` - Complete stock analysis
- `GET /api/v1/options/{symbol}` - Options chain data
- `GET /health` - Backend health check

## Disclaimers

⚠️ **Important**: This application is for educational purposes only. Not financial advice. Options trading involves significant risk.
