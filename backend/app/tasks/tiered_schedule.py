"""
BullsBears AI - Data Flow Schedule (v3.3 – November 10, 2025)
Lean, lethal, production-perfect pipeline
"""

from celery.schedules import crontab
from ..core.celery_app import celery_app

# =============================================================================
# DAILY PIPELINE – Atlanta, GA (EST/EDT) – November 10, 2025
# =============================================================================

celery_app.conf.beat_schedule.update({
    # 3:00 AM ET – FMP Premium daily delta (1-day bars only)
    'fmp-daily-delta': {
        'task': 'tasks.fmp_delta_update',
        'schedule': crontab(hour=8, minute=0, day_of_week='*'),  # 3:00 AM ET
        'options': {'queue': 'data'},
    },

    # 3:05 AM ET – Logic filter → ACTIVE (~1,700)
    'build-active-tickers': {
        'task': 'tasks.build_active_tickers',
        'schedule': crontab(hour=8, minute=5, day_of_week='*'),  # 3:05 AM ET
        'options': {'queue': 'data'},
    },

    # 3:10 AM ET – RunPod serverless: FinMA-7b → exactly 75 SHORT_LIST
    'finma-prescreen': {
        'task': 'tasks.run_finma_prescreen',
        'schedule': crontab(hour=8, minute=10, day_of_week='*'),  # 3:10 AM ET
        'options': {'queue': 'runpod'},
    },

    # 3:15 AM ET – Generate 75 charts (Matplotlib)
    'generate-charts': {
        'task': 'tasks.generate_charts',
        'schedule': crontab(hour=8, minute=15, day_of_week='*'),  # 3:15 AM ET
        'options': {'queue': 'vision'},
    },

    # 3:16 AM ET – Groq Vision → 6 boolean flags
    'groq-vision': {
        'task': 'tasks.run_groq_vision',
        'schedule': crontab(hour=8, minute=16, day_of_week='*'),  # 3:16 AM ET
        'options': {'queue': 'vision'},
    },

    # 3:17 AM ET – Grok API → social score + news + Polymarket
    'grok-social-context': {
        'task': 'tasks.run_grok_social',
        'schedule': crontab(hour=8, minute=17, day_of_week='*'),  # 3:17 AM ET
        'options': {'queue': 'social'},
    },

    # 3:20 AM ET – Rotating Arbitrator → 3–6 final picks
    'final-arbitration': {
        'task': 'tasks.run_arbitrator',
        'schedule': crontab(hour=8, minute=20, day_of_week='*'),  # 3:20 AM ET
        'options': {'queue': 'arbitrator'},
    },

    # 3:25 AM ET – Push picks to Firebase
    'publish-picks': {
        'task': 'tasks.publish_to_firebase',
        'schedule': crontab(hour=8, minute=25, day_of_week='*'),  # 3:25 AM ET
        'options': {'queue': 'publish'},
    },

    # 4:01 AM ET – BrainAgent + LearnerAgent → hot-reload 3 files
    'brain-nightly-cycle': {
        'task': 'tasks.run_brain_cycle',
        'schedule': crontab(hour=9, minute=1, day_of_week='*'),   # 4:01 AM ET
        'options': {'queue': 'learning'},
    },

    # Emergency retrain check (every 30 min during market hours)
    'emergency-check': {
        'task': 'tasks.check_emergency_retrain',
        'schedule': crontab(minute='*/30', hour='14-20', day_of_week='1-5'),  # 9:30 AM – 4:00 PM ET
        'options': {'queue': 'learning'},
    },
})

# =============================================================================
# TIMEZONE & ROUTING
# =============================================================================
celery_app.conf.timezone = 'US/Eastern'  # Auto-handles DST

celery_app.conf.task_routes.update({
    'tasks.fmp_delta_update': {'queue': 'data'},
    'tasks.build_active_tickers': {'queue': 'data'},
    'tasks.run_finma_prescreen': {'queue': 'runpod'},
    'tasks.generate_charts': {'queue': 'vision'},
    'tasks.run_groq_vision': {'queue': 'vision'},
    'tasks.run_grok_social': {'queue': 'social'},
    'tasks.run_arbitrator': {'queue': 'arbitrator'},
    'tasks.publish_to_firebase': {'queue': 'publish'},
    'tasks.run_brain_cycle': {'queue': 'learning'},
    'tasks.check_emergency_retrain': {'queue': 'learning'},
})

# =============================================================================
# COST & SAFETY LIMITS
# =============================================================================
celery_app.conf.task_time_limit = {
    'tasks.run_finma_prescreen': 300,      # 10 min
    'tasks.run_groq_vision': 180,          # 3 min
    'tasks.run_grok_social': 180,          # 3 min
    'tasks.run_arbitrator': 60,            # 2 min
    'tasks.run_brain_cycle': 600,          # 8 min
}

celery_app.conf.task_default_retry_delay = 60   # 1 min
celery_app.conf.task_max_retries = 3