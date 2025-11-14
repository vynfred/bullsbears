# app/tasks/run_learner.py
from app.core.celery import celery_app
from app.services.learner import run_nightly_learning

@celery_app.task
def trigger_learner():
    import asyncio
    asyncio.run(run_nightly_learning())