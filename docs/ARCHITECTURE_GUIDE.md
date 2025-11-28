# BullsBears v5 Architecture Guide – November 2025
Fully serverless · Zero laptop · $8–$18/month total · Never sleeps to $0 on weekends

BULLSBEARS_ARCHITECTURE = {
    "Render.com": "FastAPI web service + Background Workers + Postgres + Redis + Cron Jobs",
    "Fireworks.ai": "qwen2.5-72b-instruct → prescreen (75) + arbitrator (3–6 picks) + nightly learner",
    "Groq": "Llama-3.2-11B-Vision → 75 charts → 6 boolean flags (instant, <1 min total)",
    "xAI Grok API": "Grok-4 → social score –5 to +5 + headlines + Polymarket odds",
    "Firebase Hosting": "Next.js 15 frontend (edge global CDN)",
    "Firebase Realtime Database / Firestore": "Instant picks push + user watchlists + live stats",
    "Integration": "Each service does ONE job perfectly – no local code, no Dockerfiles, no .env"
}

## HOW THEY WORK TOGETHER (2025 FINAL)

### RENDER.COM HANDLES EVERYTHING THAT USED TO BE “LOCAL”
| Component                  | Render Service Type       | Cost (25 trading days | Notes |
|----------------------------|---------------------------|------------------------|-------|
| FastAPI backend            | Web Service (Python)      | Free tier (always warm) | Zero cold starts |
| Celery workers (all tasks) | Background Worker         | Free tier              | 512 MB → 2 GB RAM plans available |
| Daily scheduler (beat)      | Cron Job (every minute)   | Free                   | Replaces old celery_scheduler.py |
| PostgreSQL (90-day primes + tracking) | Render Postgres        | Free 90 days → $7/mo   | 10 GB storage included |
| Redis (Celery broker + cache) | Render Redis             | Free 25 MB (plenty)    | Upstash optional later |
| Chart generation (75 PNGs) | Same Background Worker     | Included               | < 0.8 s/chart, headless matplotlib |

### FIREWORKS.AI REPLACES RUNPOD 100 %
| Task                | Model                          | Fireworks endpoint                                              | Daily cost |
|---------------------|--------------------------------|------------------------------------------------------------------|------------|
| Prescreen           | qwen2.5-72b-instruct          | accounts/fireworks/models/qwen2.5-72b-instruct                   | ~$0.16 |
| Final Arbitrator    | qwen2.5-72b-instruct          | same model                                                       | ~$0.012 |
| Weekly Learner      | qwen2.5-72b-instruct          | same model – analyzes weekly outcomes, updates weights Saturday 4 AM | ~$0.04/week |

### CLOUD APIs (unchanged but cheaper)
| Service      | Model / Endpoint                                 | Daily cost |
|--------------|--------------------------------------------------|------------|
| Vision       | Groq → llama-3.2-11b-vision-instruct             | ~$0.13 |
| Social       | Grok Grok-4 (xAI API)                              | ~$0.70 |
| Market data  | Financial Modeling Prep (FMP) Premium             | <$0.05 |

### FIREBASE (frontend + realtime)
- Hosting → Next.js 15 (free tier forever)
- Realtime Database → latest picks, stats, moon/rug count (free tier covers 10k concurrent)

## DAILY WORKFLOW – 2025 EDITION (8:00 AM – 8:25 AM ET)

| Time        | Service                  | What happens                                                                 |
|-------------|--------------------------|-------------------------------------------------------------------------------|
| 8:00 AM     | Render Cron Job          | Triggers fmp_delta_update → pulls 1-day bars only                            |
| 8:05 AM     | Render Worker            | build_active_symbols → ~1,700 active tickers                                  |
| 8:10 AM     | Render Worker → Fireworks | run_prescreen → qwen2.5-72b → exactly 75 ranked candidates                   |
| 8:14 AM     | Render Worker             | generate_charts → 75 PNGs (Matplotlib headless)                              |
| 8:16 AM     | Render Worker → Groq     | run_groq_vision → 6 boolean flags per chart                                  |
| 8:17 AM     | Render Worker → Grok API | run_grok_social → sentiment –5 to +5 + headlines                             |
| 8:20 AM     | Render Worker → Fireworks | run_arbitrator → 3–6 final picks with targets & reasoning                 |
| 8:22 AM     | Render Worker             | publish_to_firebase → users see picks instantly                               |
| 4:00 AM Saturday | Render Cron Job → Fireworks | run_weekly_learner → qwen2.5-72b analyzes week's outcomes → updates weights.json & bias |

Result → Users get real-time alpha. Bot gets smarter every single night.  
Total monthly cost (25 trading days): **$8–$18** (Render $0–$7 + Fireworks/Groq/Grok ≈ $12–$14)

## ENVIRONMENT VARIABLES (only 11 – all set in Render dashboard – NO .env file ever again)

DATABASE_URL
REDIS_URL
FIREWORKS_API_KEY
GROQ_API_KEY
GROK_API_KEY
FMP_API_KEY
FIREBASE_SERVICE_ACCOUNT (full JSON)
ENVIRONMENT=production
NEXT_PUBLIC_API_URL=https://yourapp.onrender.com
KILL_SWITCH_VIX_THRESHOLD=35
KILL_SWITCH_SPY_DROP_PCT=2.0

## FILE STRUCTURE (final – 28 files total)

backend/
├── app/
│   ├── main.py
│   ├── celery_app.py
│   ├── core/(config.py, database.py, firebase.py)
│   ├── tasks/(all 10 task files)
│   ├── api/v1/(analytics.py, stocks.py, watchlist.py, internal.py)
│   ├── services/cloud_agents/(prescreen_agent.py, vision_agent.py, social_agent.py, arbitrator_agent.py, learner_agent.py)
│   ├── services/prompts/(all prompts + weights + bias)
│   └── models/
├── celery_worker.py
├── render.yaml              ← one file deploys everything
└── requirements.txt

frontend/ → deployed separately to Firebase Hosting 

