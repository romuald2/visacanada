"""Celery configuration and app instance."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "visacanada",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Toronto",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="default",
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    # IRCC monitoring Mon/Wed/Fri at 8:00 AM ET
    "ircc-monitor-mwf": {
        "task": "app.tasks.ircc_tasks.monitor_ircc_updates",
        "schedule": crontab(hour=8, minute=0, day_of_week="mon,wed,fri"),
        "options": {"queue": "monitoring"},
    },
    # Deadline / alert engine: daily scan + delivery at 7:00 AM ET
    "deadline-scan-daily": {
        "task": "app.tasks.alert_tasks.scan_deadlines",
        "schedule": crontab(hour=7, minute=0),
        "options": {"queue": "monitoring"},
    },
}
