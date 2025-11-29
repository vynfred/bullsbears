# backend/app/core/celery_app.py
"""
BullsBears v5 Celery App – Render Edition (November 2025)
Uses Render Redis (internal REDIS_URL) — zero config, zero cost
"""

import os
from celery import Celery

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
        "app.tasks.build_active_symbols",
        "app.tasks.run_prescreen",
        "app.tasks.generate_charts",
        "app.tasks.run_groq_vision",
        "app.tasks.run_grok_social",
        "app.tasks.run_arbitrator",
        "app.tasks.publish_to_firebase",
        "app.tasks.run_learner",
        "app.tasks.statistics_tasks",
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

# Optional: for local testing
if __name__ == "__main__":
    celery_app.start()