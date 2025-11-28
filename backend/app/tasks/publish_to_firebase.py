# backend/app/tasks/publish_to_firebase.py
import logging
from app.core.celery_app import celery_app
from app.services.push_picks_to_firebase import publish_picks_to_firebase

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.publish_to_firebase")
def publish_to_firebase(picks_data: dict):
    """Called by run_arbitrator after picks are made"""
    publish_picks_to_firebase(picks_data)
    logger.info("Picks published to Firebase")
    return {"status": "published"}