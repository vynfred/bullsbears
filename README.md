# BullsBears v5 - AI Trading Platform

Fully serverless architecture with Render.com + Firebase + AI agents.

## Structure

```
bullsbears/
├── render.yaml               # Render.com deployment config
├── backend/                  # FastAPI + Celery + AI agents
│   ├── app/
│   ├── celery_worker.py
│   └── requirements.txt
└── frontend/                 # Next.js dashboard
    ├── package.json
    └── ...
```

## What the Build Does

1. **Web Service**: Installs Python dependencies, starts FastAPI server on assigned port
2. **Background Worker**: Installs Python dependencies, starts Celery worker for AI tasks
3. **Cron Job**: Installs Python dependencies, runs daily market data pipeline at 8 AM ET weekdays

All services use `backend/` as root directory and pull from the same GitHub repo.

