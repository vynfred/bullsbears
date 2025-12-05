# backend/app/core/celery_app.py
"""
BullsBears v5 Celery App – Render Edition (November 2025)
Uses Render Redis (internal REDIS_URL) — zero config, zero cost
"""

import os
from celery import Celery
from celery.schedules import crontab

# Use REDIS_URL from Render environment (internal)
REDIS_URL = os.environ["REDIS_URL"]

# Fix for Render's rediss:// SSL - add ssl_cert_reqs parameter
if REDIS_URL.startswith("rediss://") and "ssl_cert_reqs" not in REDIS_URL:
    REDIS_URL = REDIS_URL + ("&" if "?" in REDIS_URL else "?") + "ssl_cert_reqs=CERT_NONE"

# Create Celery app
celery_app = Celery(
    "bullsbears",
    broker=REDIS_URL,
    backend=REDIS_URL,  # same Redis for results + broker
    include=[
        "app.tasks.fmp_delta_update",
        "app.tasks.fmp_bootstrap",
        "app.tasks.build_active_symbols",
        "app.tasks.run_prescreen",
        "app.tasks.generate_charts",
        "app.tasks.run_vision",
        "app.tasks.run_grok_social",
        "app.tasks.run_arbitrator",
        "app.tasks.publish_to_firebase",
        "app.tasks.run_learner",
        "app.tasks.statistics_tasks",
        "app.tasks.monitor_pick_outcomes",
        "app.tasks.fetch_short_interest",
        "app.tasks.fetch_fred_calendar",
    ],
)

# Minimal, battle-tested config for Render
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="US/Eastern",
    enable_utc=False,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Results
    result_expires=3600,
    result_backend=REDIS_URL,

    # Broker
    broker_url=REDIS_URL,
    broker_connection_retry_on_startup=True,

    # Concurrency — Render Background Worker (free tier = 512MB → 1 worker)
    worker_concurrency=1,
)

# Auto-discover tasks in app/tasks/
celery_app.autodiscover_tasks()

# Celery Beat Schedule - Scheduled Tasks
celery_app.conf.beat_schedule = {
    # ═══════════════════════════════════════════════════════════════════════
    # DAILY DATA REFRESH (runs before market open)
    # ═══════════════════════════════════════════════════════════════════════

    # 3:00 AM ET - FMP delta update (fetch latest OHLC for ACTIVE stocks)
    "fmp-delta-update-daily": {
        "task": "tasks.fmp_delta_update",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default"},
    },

    # 4:00 AM ET - Finnhub short interest (for all ACTIVE stocks)
    "fetch-short-interest-daily": {
        "task": "tasks.fetch_short_interest",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "default"},
    },

    # 4:30 AM ET - FRED economic calendar (upcoming high-impact events)
    "fetch-fred-calendar-daily": {
        "task": "tasks.fetch_fred_calendar",
        "schedule": crontab(hour=4, minute=30),
        "options": {"queue": "default"},
    },

    # ═══════════════════════════════════════════════════════════════════════
    # DAILY PICKS PIPELINE (runs before market open, 8:00-8:30 AM ET)
    # ═══════════════════════════════════════════════════════════════════════

    # 8:00 AM ET - Prescreen: Select ~75 candidates from ACTIVE tier
    "run-prescreen-daily": {
        "task": "tasks.run_prescreen",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "default"},
    },

    # 8:10 AM ET - Generate charts for shortlist candidates
    "generate-charts-daily": {
        "task": "tasks.generate_charts",
        "schedule": crontab(hour=8, minute=10),
        "options": {"queue": "default"},
    },

    # 8:15 AM ET - Vision analysis (chart pattern detection)
    "run-vision-daily": {
        "task": "tasks.run_vision",
        "schedule": crontab(hour=8, minute=15),
        "options": {"queue": "default"},
    },

    # 8:17 AM ET - Social/Grok analysis (sentiment + headlines)
    "run-social-daily": {
        "task": "tasks.run_grok_social",
        "schedule": crontab(hour=8, minute=17),
        "options": {"queue": "default"},
    },

    # 8:20 AM ET - Arbitrator: Select final 3-6 picks
    "run-arbitrator-daily": {
        "task": "tasks.run_arbitrator",
        "schedule": crontab(hour=8, minute=20),
        "options": {"queue": "default"},
    },

    # 8:30 AM ET - Publish picks to Firebase (triggers push notifications)
    "publish-to-firebase-daily": {
        "task": "tasks.publish_to_firebase",
        "schedule": crontab(hour=8, minute=30),
        "options": {"queue": "default"},
    },

    # ═══════════════════════════════════════════════════════════════════════
    # OUTCOME MONITORING (runs during/after market hours)
    # ═══════════════════════════════════════════════════════════════════════

    # 10:00 AM ET - Check for overnight target hits
    "monitor-pick-outcomes-morning": {
        "task": "app.tasks.monitor_pick_outcomes.monitor_pick_outcomes",
        "schedule": crontab(hour=10, minute=0),
        "options": {"queue": "default"},
    },

    # 4:30 PM ET - Check for EOD target hits + mark expired as loss
    "monitor-pick-outcomes-daily": {
        "task": "app.tasks.monitor_pick_outcomes.monitor_pick_outcomes",
        "schedule": crontab(hour=16, minute=30),
        "options": {"queue": "default"},
    },

    # ═══════════════════════════════════════════════════════════════════════
    # NIGHTLY MAINTENANCE (runs after market close)
    # ═══════════════════════════════════════════════════════════════════════

    # 11:00 PM ET - Learner: Analyze outcomes + update agent biases
    "run-learner-nightly": {
        "task": "app.tasks.run_learner.run_learner",
        "schedule": crontab(hour=23, minute=0),
        "options": {"queue": "default"},
    },

    # 11:30 PM ET - Refresh statistics cache
    "update-statistics-cache-nightly": {
        "task": "tasks.update_statistics_cache",
        "schedule": crontab(hour=23, minute=30),
        "options": {"queue": "default"},
    },

    # Weekly: Rebuild ACTIVE symbols list (Sunday 2 AM ET)
    "build-active-symbols-weekly": {
        "task": "tasks.build_active_symbols",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday
        "options": {"queue": "default"},
    },
}

# Optional: for local testing
if __name__ == "__main__":
    celery_app.start()