"""
Celery configuration for background tasks.
"""
import os
from celery import Celery
from .config import settings

# Create Celery instance
celery_app = Celery(
    "bullsbears",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.precompute",
        "app.tasks.performance_updater"
    ]
)

# Configure Celery
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.precompute.*": {"queue": "precompute"},
        "app.tasks.performance_updater.*": {"queue": "performance"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Beat schedule for precomputed analysis
    beat_schedule={
        # Market hours: every hour from 9:30 AM to 4:00 PM ET
        "precompute-market-hours": {
            "task": "app.tasks.precompute.update_top_stocks",
            "schedule": 3600.0,  # Every hour
            "options": {"queue": "precompute"},
            "kwargs": {"market_hours": True}
        },
        
        # After hours: every 2 hours
        "precompute-after-hours": {
            "task": "app.tasks.precompute.update_top_stocks",
            "schedule": 7200.0,  # Every 2 hours
            "options": {"queue": "precompute"},
            "kwargs": {"market_hours": False}
        },
        
        # Daily news update
        "precompute-daily-news": {
            "task": "app.tasks.precompute.update_news_data",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "precompute"}
        },
        
        # Cache cleanup
        "cleanup-expired-cache": {
            "task": "app.tasks.precompute.cleanup_expired_cache",
            "schedule": 3600.0,  # Every hour
            "options": {"queue": "precompute"}
        }
    },
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks()

if __name__ == "__main__":
    celery_app.start()
