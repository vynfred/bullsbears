# BullsBears v5.1 Architecture – December 2025

## Infrastructure

| Service | Purpose |
|---------|---------|
| **Render.com** | FastAPI + Celery + PostgreSQL + Redis |
| **Fireworks.ai** | Prescreen + Learner (qwen2.5-72b-instruct) |
| **xAI Grok** | Arbitrator (grok-4.1-fast) + Social (grok-4) |
| **Groq** | Vision (llama-3.2-11b-vision) |
| **FMP API** | Market data (OHLC, fundamentals) |
| **Firebase** | Frontend + Realtime DB |

## Stock Tiers

```
ALL (6,960 NASDAQ)
    ↓  Weekly (Sunday 2 AM)
ACTIVE (~2,500) — volume ≥ 100K, price ≥ $1
    ↓  Daily (8:00 AM)
SHORT_LIST (75)
    ↓  Arbitrator (8:20 AM)
PICKS (3-6) — bullish + bearish
```

## Daily Pipeline (Weekdays)

| Time | Step | Model |
|------|------|-------|
| 3:00 AM | FMP Delta | — |
| 8:00 AM | Prescreen | qwen2.5-72b |
| 8:10 AM | Charts | matplotlib |
| 8:15 AM | Vision | llama-3.2-11b-vision |
| 8:17 AM | Social | grok-4 |
| 8:20 AM | Arbitrator | grok-4.1-fast |
| 8:30 AM | Publish | Firebase |

**Weekly:** Sunday 2 AM ACTIVE rebuild · Saturday 4 AM Learner

## Database (v5 Schema)

**picks:** symbol, direction, confidence, target_primary/medium/moonshot, confluence_score, confluence_methods[]

**shortlist_candidates:** date, symbol, rank, prescreen_score, vision_flags, social_score, was_picked

**pick_outcomes_detailed:** pick_id, hit_primary/medium/moonshot_target, max_gain_pct, days_to_*

## Environment Variables

```
DATABASE_URL, REDIS_URL
FIREWORKS_API_KEY, GROK_API_KEY, GROQ_API_KEY, FMP_API_KEY
FIREBASE_SERVICE_ACCOUNT
```

## Admin Endpoints

```
POST /admin/reset-pipeline-tables
POST /admin/build-active
POST /admin/prime-data?mode=bootstrap|catchup
POST /admin/trigger-full-pipeline
GET  /admin/data/freshness
GET  /admin/data/activity
```
