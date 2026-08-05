"""Celery tasks for the deadline / alert engine.

Runs a daily scan of all active dossiers for approaching deadlines and
document expiries, then delivers any newly-created alerts across the
channels configured per dossier (dashboard / email / whatsapp).
"""

import asyncio

from app.core.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.alert_service import alert_service


async def _run_deadline_scan() -> dict:
    """Async implementation: scan all dossiers then deliver pending alerts."""
    async with async_session_factory() as session:
        stats = await alert_service.scan_and_deliver(session)
    return stats


@celery_app.task(name="app.tasks.alert_tasks.scan_deadlines")
def scan_deadlines() -> dict:
    """Celery task: scan dossiers for deadlines and deliver alerts.

    Runs daily at 7:00 AM ET via Celery Beat. Can also be triggered
    manually via the alerts API.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_deadline_scan())
    finally:
        loop.close()
