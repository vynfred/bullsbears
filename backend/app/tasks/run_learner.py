from datetime import date, timedelta
import asyncio
from celery import shared_task
from app.services.cloud_agents.learner_agent import run_weekly_learner
from app.services.system_state import is_system_on

@shared_task(name="app.tasks.run_learner.run_learner")
def run_learner():
    # Note: is_system_on is async, need to run it in event loop
    if not asyncio.run(is_system_on()):
        return {"status": "skipped", "system_off": True}

    today = date.today()
    week_end = today - timedelta(days=today.weekday() + 1)   # last Sunday
    week_start = week_end - timedelta(days=6)

    return asyncio.run(run_weekly_learner(week_start, week_end))