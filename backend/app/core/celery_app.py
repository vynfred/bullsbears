"""
Celery app instance for importing in tasks.
"""

from .celery import celery_app

__all__ = ["celery_app"]
