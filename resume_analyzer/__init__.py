"""
Expose the Celery application instance when Django starts.

Celery auto-discovery looks for tasks.py modules in INSTALLED_APPS.
"""

from __future__ import annotations

from core.celery import app as celery_app

__all__ = ("celery_app",)
