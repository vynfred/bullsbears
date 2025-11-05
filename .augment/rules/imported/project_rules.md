---
type: "always_apply"
---

# BullsBears.xyz - AI Agent Build Rules

## MANDATORY AI AGENT WORKFLOW RULES

### Rule 1: Roadmap Update After Each Task ⚠️ REQUIRED
At the end of every AI agent task, this roadmap MUST be updated to:
- Mark completed tasks as ✅ COMPLETED with timestamps
- Update progress percentages and current phase status
- Add new tasks discovered during development
- Adjust timelines based on actual progress vs. estimates
- Document blockers, dependencies, or technical discoveries
- Update success metrics and milestone completion

### Rule 2: Agent Prompt Update After Roadmap Changes ⚠️ REQUIRED
After every roadmap update, `AI_AGENT_PROMPT.md` MUST be updated to:
- Reflect new immediate priorities from roadmap progress
- Add granular, actionable tasks for next deliverables
- Update technical requirements based on development discoveries
- Revise success criteria and file structure focus
- Adjust development approach based on lessons learned

### Rule 3: Confirmation Questions Before New Tasks ⚠️ REQUIRED
Before starting new work, AI agent MUST ask clarifying questions:
- Priority confirmation based on updated roadmap
- Approach options for upcoming features
- Timeline adjustments based on discoveries
- Technical constraint clarifications
- Requirement refinements or changes

## PROJECT BUILD RULES

PROJECT BUILD RULES
Architecture Requirements

Backend: Python/FastAPI with async endpoints, PostgreSQL, Redis caching, Celery for background tasks (e.g., daily scans and backtesting)
Frontend: Next.js 15 with App Router, Tailwind CSS, mobile-first design
AI Integration: Dual AI system (Grok + DeepSeek) with consensus engine; repurposed for "When Moon?" and "When Rug?" tools
Data Sources: Alpha Vantage (quotes, indicators, news), yfinance (bulk OHLCV data), Finnhub (earnings calendar, news), NewsAPI, Reddit API, X API (for social sentiment, CEO activity, keyword searches)
Deployment: Docker containerization, Firebase hosting planned
Libraries: TA-Lib for technical indicators, scikit-learn for simple ML in self-training, NLTK/VADER as sentiment fallback

Specialized Dual AI System Rules

Grok (xAI): Technical analysis (RSI, MACD, Bollinger Bands, volume surges, Greeks if options-tied), fundamental data, mathematical calculations, backtesting pattern recognition
DeepSeek: Sentiment analysis (news, social media from X/Reddit), narrative synthesis, qualitative factors (e.g., CEO activity levels, bullish/bearish keywords like "moon/rocket" or "rug/dump")
Consensus Engine: Agreement thresholds with confidence boosting/reduction; weighted scoring (e.g., 40% technical, 30% sentiment, 20% earnings, 10% social)
A/B Testing: Performance validation and tracking over time, including backtest accuracy and alert outcomes
Self-Training Integration: Use DB-stored alert outcomes for weekly retraining (e.g., RandomForest on features); fine-tune DeepSeek on labeled data for improved sentiment classification

Tool-Specific Rules

"When Bullish?" Tool: Identifies patterns for significant upward stock movements via AI/ML analysis and daily scans. Features: Technical indicators, volume analysis, sentiment scores, earnings catalysts, social media activity.
"When Bearish?" Tool: Identifies patterns for significant downward stock movements via AI/ML analysis. Features: Technical indicators, volume analysis, sentiment scores, earnings risks, social media sentiment.
AI/ML System: 82-feature system (74 base + 8 AI features) with ensemble models delivering realistic predictions (48-52% bullish, 27-45% bearish).
Daily Scans: Automated scanning of volatile tickers; generate bullish/bearish picks with confidence scores and target ranges.
Watchlist System: Users can add AI picks or custom stocks to personal watchlist; track performance vs AI picks.
Alerts: DB-recorded with timestamp, features, confidence; exposed via API endpoints (/api/v1/bullish_alerts, /api/v1/bearish_alerts).

Development Rules
1. Build-First Philosophy

NO PAYMENT/SUBSCRIPTION FEATURES during development phase
All features available to all users during MVP development
No rate limiting beyond basic demo protection
Monetization is Phase 4 (months away)

2. Mobile-First Approach

Design for mobile screens first (320px+)
Use responsive Tailwind classes (sm:, md:, lg:)
Touch-friendly buttons (min 44px height)
Readable text sizes on small screens

3. Performance Requirements

API endpoints: < 200ms average
Dual AI analysis: < 500ms with parallel processing
Backtesting runs: Offline/weekend execution to avoid real-time delays
Daily scans: < 5 minutes total for 200 tickers
Page load times: < 3 seconds
Database queries: < 50ms average

4. User Experience Rules

Clear loading states with progress indicators (e.g., for scans/backtests)
Helpful error messages with retry options
Intuitive navigation and information hierarchy (e.g., dashboard tabs for Bullish/Bearish alerts)
Consistent bull/bear branding throughout with professional design
Stock identification display rules:
- Always show actual stock tickers (TSLA, NVDA, AAPL, etc.) since no bias concerns with AI-only approach
- Clear AI confidence scores and reasoning for transparency
- Target price ranges and estimated timeframes for all picks

5. Legal Safety Requirements (CRITICAL)

"Not Financial Advice" disclaimer on every page
"Do Your Own Research (DYOR)" warnings
Risk disclaimers for options trading and high-volatility predictions
No auto-execution or broker integration
Disclaimers in alerts: "Based on patterns; past performance ≠ future results"

6. Security Rules

HTTPS enforcement for all connections
Input validation and sanitization (e.g., ticker symbols)
Rate limiting (100 requests/minute per user)
Secure API key management via environment variables (add X_API_KEY, etc.)

Code Structure Rules
Backend Structure
textbackend/
├── app/
│ ├── api/v1/ # REST API endpoints (add moon_alerts.py, rug_alerts.py)
│ ├── services/ # AI services (Grok, DeepSeek, consensus), external APIs (add x_api.py)
│ ├── analyzers/ # Data analysis engines (add backtest.py, moon_analyzer.py, rug_analyzer.py)
│ ├── models/ # Database models (extend AnalysisResult with alert_type, features_json, outcome)
│ ├── core/ # Configuration, database, Redis
│ └── tasks/ # Background jobs (Celery: add daily_scan.py, weekly_retrain.py)
Frontend Structure
textfrontend/
├── src/
│ ├── app/ # Next.js app router pages (add /moon, /rug dashboards)
│ ├── components/ # Reusable React components (e.g., AlertCard, BacktestChart)
│ ├── lib/ # API client and utilities (add fetchAlerts hook)
│ ├── hooks/ # Custom React hooks (e.g., useScanStatus)
│ └── styles/ # Tailwind CSS and themes (add moon/rug color schemes)
Caching Rules

API responses: 30 seconds
AI analysis results: 5 minutes (technical), 10 minutes (sentiment)
News data: 10 minutes
Social media data: 5 minutes
Backtest results: 1 hour (offline recompute if needed)
Scan alerts: 5 minutes
User preferences: 1 hour

Testing Rules

Unit tests for AI services and analyzers (90%+ coverage, including backtest functions)
Integration tests for API endpoints and Celery tasks
Performance tests for dual AI consensus and daily scans
Mock external API responses for reliable testing (e.g., mock X API tweets)
Component testing with React Testing Library
Mobile responsiveness testing
Backtest validation: Test accuracy on sample data (e.g., 60%+ recall)

Error Handling Rules

Graceful fallback to demo data when APIs fail (e.g., cached historical for backtests)
Clear error messages with retry options (e.g., "X API rate limit hit; retry in 1 min")
Loading states for all async operations (scans, AI prompts)
Network error detection and handling
Comprehensive try-catch blocks with circuit breakers (e.g., fallback to rule-based if AI down)

AI Tool Rules

Personal Use Only: All AI tools are for educational and personal trading analysis. Outputs must include disclaimers: "Not financial advice. Use at your own risk."
Transparency: Log all AI calls, inputs, and outputs in the database (e.g., extend AnalysisResult with ai_prompt and ai_response fields) for auditing.
Performance Focus: AI queries should complete in <500ms. Use caching (Redis TTL: 1min for similar prompts) to avoid redundant calls.
Rate Limiting Compliance: Respect API limits (e.g., xAI API quotas). Implement exponential backoff in services (e.g., services/grok.py).
No Real-Time Trading Automation: AI tools provide alerts only; no direct integration with brokerage APIs for execution.
Repurposing Existing Analyzer: Build "When Moon?" and "When Rug?" by extending the stock analyzer in analyzers/. Reuse confidence.py for scoring, adapting weights for moon/rug patterns (e.g., 40% technical, 30% sentiment).
Prompt Engineering: Prompts must be concise (<500 tokens) and specific (e.g., "Analyze sentiment for TSLA moon potential from these tweets: [list]. Score 0-1 bullish."). Include context: Always append "Base on historical patterns for 20%+ moves in 1-3 days." Handle Bias: Instruct AI to "Provide balanced analysis, avoiding hype or fear-mongering."
Fallback Mechanisms: If Grok/DeepSeek fails (e.g., rate limit), fallback to rule-based analysis (e.g., VADER for sentiment) and log the downgrade.
Data Inputs: Technical: From TA-Lib/yfinance (e.g., RSI, volume). Social: X API queries (e.g., CEO activity, keyword counts like "moon" or "rug"). News/Earnings: Finnhub/Alpha Vantage. Limit to free tiers; no paid upgrades without explicit config.
Backtesting First: Initial models use 3 months' historical data (e.g., Aug-Oct 2025). Run offline in backtest.py before any live scans.
Feedback Loop: Record alerts in DB with outcome (checked 3 days post-alert via price API). Weekly retrain: Use scikit-learn (e.g., RandomForest) on labeled data; fine-tune DeepSeek if accuracy <60%. Threshold for Alerts: Only trigger if confidence >70%; track false positives (>20% triggers retrain).
Overfitting Prevention: Use cross-validation (80/20 split). Test on out-of-sample data (e.g., recent month).
Data Retention: Store features/labels for 1 year max; anonymize (no user-specific data).
Ethical Training: Exclude manipulative patterns (e.g., pump-and-dump signals). Focus on verifiable traits like volume surges.
API Key Management: Store keys in .env only; never hardcode. Use os.getenv in code.
Input Sanitization: Validate all user inputs (e.g., tickers) to prevent injection in AI prompts.
Data Privacy: No storage of personal trading history. AI processes aggregate/public data only.
Error Handling: Catch API errors gracefully (e.g., return "AI analysis unavailable; using fallback."). Log to console/file with logging.ERROR.
Unit Tests: 90% coverage for AI-related functions (e.g., mock Grok responses in tests/test_analyzers.py).
Integration Tests: Test full pipeline (backtest → scan → alert) with sample data.
Monitoring: Add Celery task to check AI accuracy weekly; alert dev if drops below 50%.
Updates: Review rules quarterly. If xAI/DeepSeek changes (e.g., new models), test compatibility before upgrading.
Disclaimers in Outputs: Every AI-generated alert must end with: "This is based on patterns and may not predict future moves. Past performance ≠ future results."
