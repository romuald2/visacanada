"""Celery tasks for IRCC monitoring."""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.ircc_update import IRCCUpdate
from app.models.notification import Notification, NotificationChannel, NotificationType
from app.models.user import User, UserRole
from app.services.ircc_monitor import IRCCFeedParser


async def _run_ircc_monitor() -> dict:
    """Async implementation of IRCC monitoring task."""
    parser = IRCCFeedParser()
    stats = {"fetched": 0, "new": 0, "notified": 0}

    try:
        updates = await parser.fetch_all_sources()
        stats["fetched"] = len(updates)

        async with async_session_factory() as session:
            new_updates = await _store_new_updates(session, updates)
            stats["new"] = len(new_updates)

            if new_updates:
                stats["notified"] = await _notify_admins(session, new_updates)

            await session.commit()
    finally:
        await parser.close()

    return stats


async def _store_new_updates(
    session: AsyncSession, updates: list[dict]
) -> list[IRCCUpdate]:
    """Store updates that don't already exist. Returns newly created updates."""
    new_updates = []

    for update_data in updates:
        external_id = update_data["external_id"]

        # Check for duplicates
        stmt = select(IRCCUpdate).where(IRCCUpdate.external_id == external_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            ircc_update = IRCCUpdate(
                title=update_data["title"],
                content=update_data["content"],
                summary=update_data["summary"],
                category=update_data["category"],
                source=update_data["source"],
                source_url=update_data["source_url"],
                external_id=external_id,
                published_at=update_data["published_at"],
                detected_at=datetime.now(timezone.utc),
            )
            session.add(ircc_update)
            new_updates.append(ircc_update)

    if new_updates:
        await session.flush()

    return new_updates


async def _notify_admins(
    session: AsyncSession, new_updates: list[IRCCUpdate]
) -> int:
    """Create notifications for admin users about new IRCC updates."""
    # Find admin users
    stmt = select(User).where(User.role == UserRole.admin, User.is_active == True)
    result = await session.execute(stmt)
    admins = result.scalars().all()

    notified = 0
    for admin in admins:
        # Create a summary notification
        titles = [u.title[:80] for u in new_updates[:5]]
        message_parts = [f"• {t}" for t in titles]
        if len(new_updates) > 5:
            message_parts.append(f"... et {len(new_updates) - 5} autre(s)")

        notification = Notification(
            recipient_id=admin.id,
            notification_type=NotificationType.policy_update,
            channel=NotificationChannel.dashboard,
            title=f"{len(new_updates)} nouvelle(s) mise(s) à jour IRCC détectée(s)",
            message="\n".join(message_parts),
            is_read=False,
        )
        session.add(notification)
        notified += 1

    # Mark updates as notified
    for update in new_updates:
        update.is_notified = True

    return notified


@celery_app.task(name="app.tasks.ircc_tasks.monitor_ircc_updates")
def monitor_ircc_updates() -> dict:
    """Celery task: fetch IRCC feeds and store new updates.

    Runs Mon/Wed/Fri at 8:00 AM ET via Celery Beat.
    Can also be triggered manually via API.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_ircc_monitor())
    finally:
        loop.close()
