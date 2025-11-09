"""
Celery application initialisation for the Resume Analyzer project.

The Celery configuration pulls settings from django.conf settings using the
`CELERY_` namespace. Tasks are discovered automatically from installed apps.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resume_analyzer.settings")

app = Celery("resume_analyzer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

