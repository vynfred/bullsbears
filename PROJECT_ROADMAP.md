# BullsBears.xyz Project Roadmap 🚀

### Last Updated: January 13, 2025

---

## 🎯 CURRENT STATUS

### Frontend (Next.js 15)
✅ **RUNNING** at http://localhost:3000
- Main Dashboard (page.tsx): 3-tab system (Picks/Watchlist/Analytics)
- Public pages accessible via hamburger menu (How It Works, FAQ, Terms)
- Admin panel at `/admin` (hidden, no public links)
- Auth temporarily disabled for testing
- Mobile-first responsive design with dark theme
- API configured for localhost:8000 backend

### Backend (FastAPI)
⚠️ **NEEDS SETUP** - Not currently running
- **Development**: http://localhost:8000
- **Production**: Google Cloud Run (serverless, auto-scaling)
- Database: Google Cloud SQL (PostgreSQL)
- Real-time: Firebase Realtime Database
- AI Processing: RunPod serverless endpoint

---

#### Prime DB with last 90 days of data (PostgreSQL)
- TABLE prime_ohlc_90d

#### Tiered Stock Classification System
**4-Tier Pipeline**:
- **ALL (NASDAQ)**: Complete NASDAQ stock universe via FMP historical 90days to prime data (actual listed count)
- **ACTIVE (~1,700)**: Daily filtered high-potential tickers
- **SHORT_LIST (exactly 75)**: qwen2.5:32b via Runpod/huggingface pre-screened explosive candidates
- **PICKS (3–6)**: Final high-conviction daily recommendations

#### Logic and filter
**CHECK**: Kill Switch (VIX > 30 OR SPY pre-market < -2%) → return []  
**FILTER**: Daily logic filter → ACTIVE list stored in db

#### Agent Processing Pipeline (with learning loop)

Phase 1: Prescreen Agent (qwen2.5:32b) – ACTIVE → SHORT_LIST (exactly 75)
Phase 2: Chart Generation (Matplotlib) – 75 × 256×256 PNG charts (90-day + volume)
Phase 3: Vision Agent (Groq Llama-3.2-11B-Vision) – 75 charts → 6 boolean flags each
Phase 4: Social Sentiment (Grok API) – 75 sentiment scores
Phase 5: Final Arbitrator (CLoud API cycle) – ONE call → final 3–6 picks with targets, support & confidence

#### NIGHTLY LEARNING LOOP (04:01 AM – RunPod)
LearnerAgent → reads 30-day picks + outcomes → generates weights → rewrites system_prompt.txt with new weights.json

#### MODEL FOR RUNPOD:
- qwen2.5:32b: Prescreen agent (Phase 1)

#### CLOUD MODELS:
- Groq Llama-3.2-11B-Vision: Vision pattern detection (Phase 3)
- Grok API: Social sentiment (Phase 4)
- DeepSeek-V3 API: Final arbitration on cycle (Phase 5)
- Claude - Final arbitration on cycle
- ChatGpt - Final arbitration on cycle
- Gemini - Final arbitration on cycle
- Grok API: Final arbitration on cycle


#### Data Flow Architecture
1. FMP API → 90-days historical data (system prime) → PostgreSQL
2. Kill Switch: VIX >35 AND SPY <-2% override (returns [] if active)
3. Weekly: FMP refresh ALL tier + Logic filter ALL → ACTIVE
3. Daily: FMP update ACTIVE tier
4. Agent Screen via runpod: SHORT_LIST → PICKS
5. Cloud AI sentiment and final decision: PICKS
6. Learner run at night updating prompt text files as needed.
```

### Short List Tracking & Model Learning System

**Purpose**: Turn every missed bullish moon /bearish rug into permanent alpha. Track **all 75 SHORT_LIST candidates** (not just final picks) for 30 days → mine what actually worked → auto-upgrade every agent.

**Components**:
1. **Full Short List Capture**: Every qwen2.5:32b candidate + vision flags + sentiment
2. **30-Day Price Tracking**: Daily close + max gain/loss for all 75 tickers
3. **Weekly Retrospective**: “What got away?” analysis — rank rejected candidates by actual move
4. **Closed-Loop Learning**: Auto-update **three** things nightly:
   - Prescreener prompt (qwen2.5:32b)
   - Arbitrator weights
   - Vision flag importance
5. **Model-vs-Model Leaderboard**: Track hit rate per arbitrator (DeepSeek-V3 vs Gemini vs Grok 4, etc.)

**Database Schema**:
- `pick_candidates`
- `short_list_price_tracking`
- `short_list_retrospective_analysis`
- `short_list_model_learning`

Phase 0: Kill Switch Check (VIX > 35 OR SPY pre-market < -2%)
├── If triggered → continue data collection but return empty picks
└── Notify: "No picks today – market conditions too volatile"

Phase 1: Tiered Stock Classification
├── ALL (~3,800 NASDAQ) → ACTIVE (~1,700) → SHORT_LIST (exactly 75)
├── ACTIVE: Daily logic filter (price >$1.25, volume >100K, cap >$500M, volatility/surge/beta)
├── SHORT_LIST: qwen2.5:32b:32b prescreen (one call, all 127 features + vision-ready)
└── Output: 75 high-conviction explosive candidates

Phase 2: Chart Generation
├── Matplotlib (headless) → 75 × 256×256 PNG charts (90-day candles + volume)
└── Base64 stored in PostgreSQL for instant vision access

Phase 3: Vision Analysis (Groq Llama-3.2-11B-Vision)
├── 75 parallel API calls → 6 boolean visual pattern flags per ticker:
│   • wyckoff_phase_2
│   • weekly_triangle_coil
│   • volume_shelf_breakout
│   • p_shape_profile
│   • fakeout_wick_rejection
│   • spring_setup
└── Output: Vision flags stored alongside each SHORT_LIST ticker

4: Social + News + Economic Context (Grok API)
├── 75 parallel calls → single integer -5 to +5 per ticker
│   • -5 = extreme bearish panic / rug setup
│   •  0 = neutral
│   • +5 = extreme FOMO / moon chatter
├── Each call also returns:
│   • Top 3 news headlines (last 24 h)
│   • Upcoming economic events affecting the ticker/sector (next 48 h)
│   • Current Polymarket probability (if binary event exists, e.g., Fed cut, tariff vote)

Phase 5: Final Arbitration (7-day rotating frontier model)
├── ONE call per day with full context:
│   • qwen2.5:32b:32b score
│   • 6 vision flags
│   • Grok social score (-5 to +5)
│   • Top news headlines & catalysts
│   • Upcoming economic events + Polymarket probabilities
│   • LightGBM 82-feature probability
│   • Historical volatility & pattern precedents
├── Arbitrator prompt explicitly asks:
│   • "Weigh surprise potential: actual vs Polymarket-implied probability"
│   • "Factor second-order effects of Fed/tariff outcomes on this ticker"
│   • "Combine social FOMO with economic catalyst timing"
└── Output: 3–6 final picks with: 
│   • 3–6 final picks (at least 1 bearish pick)
│   • Bullish: target_low, high target, support_level based on vision, stop_loss
│   • Bearish: entry_zone, target_low, support_level
|   • Target ranges & stop/support levels
|   • Confidence %
|   • Full reasoning including economic/polymarket edge as needed
├── Rotation schedule (auto-selected by weekday):
│   Mon       → DeepSeek-V3
│   Tue       → Gemini 2.5 Pro
│   Wed       → Grok 4
│   Thu       → Claude Sonnet 4
│   Fri       → GPT-5 (o3 mode)
└── All 75 SHORT_LIST candidates + final picks logged for LearnerAgent

Phase 6: Short List Tracking & Closed-Loop Learning (Learner.py on RunPod)
├── 30-day price tracking on ALL 75 candidates
├── Nightly Learner.py (4:01 AM on RunPod) → mines missed moons/rugs
├── Learner.py hot-reloads 2 files:
│   • arbitrator/weights.json
│   • prompts/arbitrator_prompt.txt (with updated weights)
├── Weekly arbitrator leaderboard → auto-adjusts rotation weights
└── Output: System gets smarter every single night
└── NOTE: Learner.py handles all learning and prompt updates


### 🔧 **SECONDARY PRIORITIES** 


#### 8. **Performance Optimization** (LOW)
- Optimize agent response times for 2-3 second targets
- Implement caching strategies for frequently accessed data
- Fine-tune database queries for better performance
- Optimize surveillance batch processing


### Enhanced Target Analysis Framework

### AI-Determined Target Probabilities (Single Arbitrator – ONE call)
├── Vision Pattern Strength: 6 boolean flags (Wyckoff, volume shelf, etc.)
├── Technical Momentum: LightGBM 82-feature probability
├── Social + Catalyst Heat: Grok score (-5 to +5) + news + Polymarket odds
├── Historical Precedent: Exact same pattern outcomes from 30-day tracking
└── Market Regime Filter: Kill-switch + VIX overlay

### Dynamic Target Framework (Arbitrator decides everything)
├── Low Target: +15% (bullish) / –15–20 (bearish) → 70–90% implied prob
├── High Target: +30–50% (bullish) / –35–45% (bearish) 
├── Stop Loss (bullish): –5–10   % / Support Level (bearish): wherever AI decides
├── Timeframe: 1–5 trading days (auto-selected by pattern decay rate)
└── Risk/Reward: Minimum 2.5:1 enforced

### Target Setting Process (NO extra agents)
├── Arbitrator receives full context in ONE prompt:
│   • qwen2.5:32b score
│   • 6 vision flags
│   • Grok social + news + Polymarket
│   • LightGBM probability
│   • 30-day historical outcomes for identical setups
├── Arbitrator outputs final targets + probabilities + reasoning
└── LearnerAgent tracks actual vs predicted → updates weights nightly

### AI Learning & Calibration System
```
Nightly Closed Loop (4:01 AM):
├── Track all 75 SHORT_LIST candidates for 30 days
├── LearnerAgent → mines: "volume_shelf_breakout + sentiment ≥ 6 → 83% moon"
│   • prefileter.txt
│   • arbitrator/weights.json
│   • vision/flag_weights.json
├── Arbitrator leaderboard → auto-promotes winning model (Gemini > Grok 4 etc.)
└── No manual calibration ever needed
```

#### ArbitratorAgent Prompt (Current – copy-paste ready)
```text
You are the final arbitrator (today: Gemini 2.5 Pro).
You receive 75 candidates with:
- qwen2.5:32b score
- 6 vision flags
- Grok social score (-5 to +5) + top news + Polymarket odds
- LightGBM probability
- Historical outcomes for identical setups

For each pick you MUST output:
1. Direction (bullish/brearish)
2. Low target / High target / Stop or Support
3. Confidence % (realistic, not inflated)
4. One-sentence reason including vision + social + economic edge

Use Learner.py weights from /arbitrator/weights.json.
Prioritize patterns that hit high targets or greater within the shortest period of time up to 30 days.
```

---

## 📱 FRONTEND STRUCTURE (Next.js 15)

### Main Routes
- **`/`** - Main Dashboard (page.tsx)
  - Picks Tab: Bullish/Bearish AI picks with live data
  - Watchlist Tab: User's tracked stocks
  - Analytics Tab: Performance metrics and accuracy trends

- **`/admin`** - Admin Control Panel (hidden, no public links)
  - System ON/OFF toggle
  - Prime Data button (load 90 days historical)
  - Database connection status (Google SQL, Firebase)
  - API status checks (FMP, Groq, Grok, DeepSeek)
  - RunPod endpoint status
  - ⚠️ NO dummy data - only real status checks

### Hamburger Menu Pages (Accessible to All)
- How It Works
- FAQ
- Terms & Privacy
- Profile (future)
- Settings (future)

### Authentication Status
- ⚠️ Auth temporarily disabled for testing
- Middleware allows all routes without login
- Future: Firebase Auth will be implemented
- Goal: Test backend/frontend integration first, then add auth

### API Configuration
- Development: `http://localhost:8000` (FastAPI backend)
- Environment: `.env.local` with `NEXT_PUBLIC_API_URL`
- No mock data - frontend shows empty states when backend is offline

---

## 🔧 NEXT IMMEDIATE STEPS

### 1. Backend Setup (PRIORITY)
- [ ] Get FastAPI backend running on localhost:8000
- [ ] Connect to Google Cloud SQL (IP whitelist: 24.99.57.192)
- [ ] Test `/health` endpoint
- [ ] Test `/api/v1/admin/status` endpoint

### 2. Data Priming (FIRST TASK)
- [ ] Implement `/api/v1/admin/prime-data` endpoint
- [ ] Load 90 days OHLC data for ~6,960 NASDAQ stocks
- [ ] Store in Google Cloud SQL `prime_ohlc_90d` table
- [ ] Verify data loaded correctly

### 3. Frontend Testing
- [ ] Verify all tabs load without errors
- [ ] Test empty states (no data from backend)
- [ ] Test admin panel status checks
- [ ] Confirm no mock data is being used

### 4. Integration Testing
- [ ] Frontend → Backend API calls
- [ ] Database queries working
- [ ] Firebase connection working
- [ ] Real-time updates functioning

---