# Celery Worker & Beat Deployment Guide

## Overview

BullsBears uses Celery for scheduled background tasks:
- **Celery Worker**: Executes tasks (data updates, AI agents, etc.)
- **Celery Beat**: Scheduler that triggers tasks at specific times
- **Redis**: Message broker and result backend

## Architecture

```
┌─────────────────┐
│  Celery Beat    │ ──> Schedules tasks (cron-like)
│  (Scheduler)    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│     Redis       │ ──> Message queue
│   (Broker)      │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Celery Worker   │ ──> Executes tasks
│  (Executor)     │
└─────────────────┘
```

## System State Control

**IMPORTANT**: All tasks check `SystemState.is_system_on()` before executing.
- System state is stored in Firebase at `/system/state`
- Admin panel controls ON/OFF state
- When OFF, tasks are scheduled but skip execution
- State persists across restarts and sessions

## Task Queues

Tasks are organized into queues for better resource management:

- **data**: FMP updates, ACTIVE tier filtering, statistics
- **runpod**: Prescreen (Qwen2.5:32b), Weekly Learner
- **vision**: Chart generation, Groq Vision API
- **social**: Grok Social API
- **arbitrator**: Final pick selection (rotating cloud models)
- **publish**: Firebase publishing

## Daily Schedule (EST/EDT)

```
8:00 AM - FMP Delta Update (data queue)
8:05 AM - Build ACTIVE Symbols (data queue)
8:10 AM - Prescreen: ACTIVE → SHORT_LIST (runpod queue) 🔥 GPU
8:15 AM - Generate Charts (vision queue)
8:16 AM - Groq Vision Analysis (vision queue)
8:17 AM - Grok Social Analysis (social queue)
8:20 AM - Final Arbitrator (arbitrator queue)
8:25 AM - Publish to Firebase (publish queue)

Every 5 min - Statistics Cache Update (data queue)
Every 2 min (market hours) - Badge Data Update (data queue)
Every hour - Statistics Validation (data queue)
Daily 12 PM - Statistics Report (data queue)

Saturday 4:00 AM - Weekly Learner (runpod queue) 🔥 GPU
```

## Option 1: Deploy to Cloud Run (Recommended for MVP)

### Prerequisites
- Redis instance (Cloud Memorystore or external Redis)
- Google Cloud SQL (PostgreSQL)
- Firebase Realtime Database
- All API keys in environment variables

### 1. Deploy Celery Worker

Create `backend/Dockerfile.worker`:
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gcc g++ wget unzip \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ && ./configure --prefix=/usr && make && make install \
    && cd .. && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Run Celery Worker
CMD celery -A app.core.celery worker --loglevel=info --concurrency=4
```

Deploy to Cloud Run:
```bash
gcloud run deploy bullsbears-celery-worker \
  --source backend \
  --dockerfile backend/Dockerfile.worker \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://...,CELERY_BROKER_URL=redis://...,CELERY_RESULT_BACKEND=redis://..." \
  --min-instances=1 \
  --max-instances=1 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600
```

### 2. Deploy Celery Beat

Create `backend/Dockerfile.beat`:
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Run Celery Beat
CMD celery -A app.core.celery beat --loglevel=info
```

Deploy to Cloud Run:
```bash
gcloud run deploy bullsbears-celery-beat \
  --source backend \
  --dockerfile backend/Dockerfile.beat \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://...,CELERY_BROKER_URL=redis://...,CELERY_RESULT_BACKEND=redis://..." \
  --min-instances=1 \
  --max-instances=1 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=3600
```

## Option 2: Local Development with Docker Compose

Use the existing `docker-compose.yml`:

```bash
# Start all services (backend, worker, beat, redis, postgres)
docker-compose up -d

# View worker logs
docker-compose logs -f celery_worker

# View beat logs
docker-compose logs -f celery_beat

# Stop all services
docker-compose down
```

## Monitoring & Debugging

### Check Task Status
```bash
# List active tasks
celery -A app.core.celery inspect active

# List scheduled tasks
celery -A app.core.celery inspect scheduled

# List registered tasks
celery -A app.core.celery inspect registered
```

### Manual Task Trigger (via Admin API)
```bash
curl -X POST http://localhost:8000/api/v1/admin/trigger-task/prescreen
```

Available tasks:
- `prescreen` - Run prescreen agent
- `arbitrator` - Run arbitrator
- `learner` - Run weekly learner
- `sync_firebase` - Publish to Firebase
- `fmp_update` - FMP data update
- `build_active` - Build ACTIVE tier
- `generate_charts` - Generate charts
- `vision` - Run vision analysis
- `social` - Run social analysis

## Cost Control

### RunPod Tasks (GPU-based)
- **Prescreen**: 15 min max timeout
- **Weekly Learner**: 15 min max timeout
- Only runs when system is ON
- Automatic shutdown after task completion

### Cloud API Tasks
- **Arbitrator**: 10 min max timeout
- **Vision**: 5 min max timeout
- **Social**: 5 min max timeout

### Redis Considerations
For MVP, you can use:
1. **Cloud Memorystore** (Google Cloud) - ~$50/month for basic tier
2. **Redis Labs** (free tier) - 30MB, good for testing
3. **Upstash** (serverless Redis) - pay per request

## Environment Variables

Required for Celery workers:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis
CELERY_BROKER_URL=redis://host:6379/1
CELERY_RESULT_BACKEND=redis://host:6379/2

# APIs
FMP_API_KEY=your_fmp_key
GROQ_API_KEY=your_groq_key
GROK_API_KEY=your_grok_key
DEEPSEEK_API_KEY=your_deepseek_key
RUNPOD_API_KEY=your_runpod_key

# Firebase
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
```

## Troubleshooting

### Tasks not executing
1. Check system state: `GET /api/v1/admin/status`
2. Verify Redis connection
3. Check worker logs for errors
4. Ensure beat scheduler is running

### RunPod tasks timing out
1. Check RunPod endpoint status
2. Verify API key is valid
3. Check task time limits in `celery_scheduler.py`

### Memory issues
1. Increase worker memory allocation
2. Reduce concurrency: `--concurrency=2`
3. Enable worker autoscaling: `--autoscale=10,3`

