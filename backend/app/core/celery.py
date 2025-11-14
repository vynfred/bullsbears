#!/usr/bin/env python3
"""
BullsBears Celery App – FINAL v3.3 (November 12, 2025)
LEAN. AUTOMATIC. $0 IDLE. NO LEGACY.
"""

import os
from celery import Celery
from .config import settings

# Create Celery app
celery_app = Celery(
    "bullsbears",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.run_finma_and_brain",
        "app.tasks.generate_charts",
        "app.tasks.run_groq_vision",
        "app.tasks.run_grok_social",
        "app.tasks.run_arbitrator",
        "app.tasks.publish_to_firebase",
        "app.tasks.fmp_delta_update",
        "app.tasks.build_active_tickers",
        "app.tasks.statistics_tasks",
    ]
)

# CONFIG — ONLY WHAT YOU NEED
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="US/Eastern",
    enable_utc=False,

    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=True,

    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    result_expires=3600,
    result_persistent=False,

    task_reject_on_worker_lost=True,
    task_acks_late=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

celery_app.autodiscover_tasks()

if __name__ == "__main__":
    celery_app.start()