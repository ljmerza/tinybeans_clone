"""Expose Celery application for ``celery -A mysite`` entrypoints."""
from .celery import app as celery_app

__all__ = ('celery_app',)
