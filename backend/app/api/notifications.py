"""WhatsApp notifications API router."""


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.whatsapp_notification import (
    NotificationPreference,
    WhatsAppNotification,
)
from app.services.whatsapp_service import (
    DEFAULT_PREFERENCES,
    whatsapp_service,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SendNotificationRequest(BaseModel):
    event: str
    to_number: str
    data: dict


class PreferencesUpdateRequest(BaseModel):
    whatsapp_number: str | None = None
    is_enabled: bool | None = None
    events: dict[str, bool] | None = None


class NotificationHistoryResponse(BaseModel):
    id: int
    event_type: str
    to_number: str
    message: str
    status: str
    channel: str | None
    sent_at: str

    model_config = {"from_attributes": True}


@router.post("/send")
async def send_notification(
    body: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Manually send a WhatsApp notification (admin only)."""
    # Get user preferences for rate limit context
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()
    preferences = prefs.events if prefs and prefs.events else None

    # Send notification
    send_result = await whatsapp_service.notify(
        event=body.event,
        to_number=body.to_number,
        data=body.data,
        preferences=preferences,
    )

    # Store in history
    message = whatsapp_service.render_template(body.event, body.data)
    notification = WhatsAppNotification(
        user_id=current_user.id,
        event_type=body.event,
        to_number=body.to_number,
        message=message,
        status=send_result["status"],
        channel=send_result.get("channel"),
        twilio_sid=send_result.get("sid"),
        error=send_result.get("error"),
        extra_data=body.data,
    )
    db.add(notification)
    await db.commit()

    return send_result


@router.post("/test")
async def test_notification(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Send a test notification to verify WhatsApp connection."""
    # Get preferences for number
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs or not prefs.whatsapp_number:
        raise HTTPException(
            status_code=400,
            detail="Numero WhatsApp non configure. Mettez a jour vos preferences.",
        )

    send_result = await whatsapp_service.send_whatsapp(
        to_number=prefs.whatsapp_number,
        message="*Test VisaCanada*\n\nVotre connexion WhatsApp fonctionne correctement.",
    )

    # Log test
    notification = WhatsAppNotification(
        user_id=current_user.id,
        event_type="test",
        to_number=prefs.whatsapp_number,
        message="Test notification",
        status=send_result["status"],
        channel=send_result.get("channel"),
        twilio_sid=send_result.get("sid"),
        error=send_result.get("error"),
    )
    db.add(notification)
    await db.commit()

    return send_result


@router.get("/history")
async def get_notification_history(
    event_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Get notification sending history."""
    query = select(WhatsAppNotification).where(
        WhatsAppNotification.user_id == current_user.id
    )

    if event_type:
        query = query.where(WhatsAppNotification.event_type == event_type)
    if status_filter:
        query = query.where(WhatsAppNotification.status == status_filter)

    query = query.order_by(WhatsAppNotification.sent_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        {
            "id": n.id,
            "event_type": n.event_type,
            "to_number": n.to_number,
            "message": n.message,
            "status": n.status.value if hasattr(n.status, "value") else n.status,
            "channel": n.channel,
            "sent_at": n.sent_at.isoformat(),
        }
        for n in notifications
    ]


@router.get("/preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get notification preferences for current user."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        return {
            "whatsapp_number": None,
            "is_enabled": True,
            "events": DEFAULT_PREFERENCES,
        }

    return {
        "whatsapp_number": prefs.whatsapp_number,
        "is_enabled": prefs.is_enabled,
        "events": prefs.events or DEFAULT_PREFERENCES,
    }


@router.put("/preferences")
async def update_preferences(
    body: PreferencesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Update notification preferences."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreference(
            user_id=current_user.id,
            whatsapp_number=body.whatsapp_number,
            is_enabled=body.is_enabled if body.is_enabled is not None else True,
            events=body.events or DEFAULT_PREFERENCES,
        )
        db.add(prefs)
    else:
        if body.whatsapp_number is not None:
            prefs.whatsapp_number = body.whatsapp_number
        if body.is_enabled is not None:
            prefs.is_enabled = body.is_enabled
        if body.events is not None:
            prefs.events = body.events

    await db.commit()

    return {
        "message": "Preferences mises a jour",
        "whatsapp_number": prefs.whatsapp_number,
        "is_enabled": prefs.is_enabled,
        "events": prefs.events,
    }


@router.get("/stats")
async def get_notification_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Get notification statistics."""
    # Total sent
    total_result = await db.execute(
        select(func.count(WhatsAppNotification.id))
    )
    total = total_result.scalar() or 0

    # By status
    sent_result = await db.execute(
        select(func.count(WhatsAppNotification.id)).where(
            WhatsAppNotification.status == "sent"
        )
    )
    sent = sent_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(WhatsAppNotification.id)).where(
            WhatsAppNotification.status == "failed"
        )
    )
    failed = failed_result.scalar() or 0

    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "rate_limited": total - sent - failed,
        "success_rate": round((sent / total * 100), 1) if total > 0 else 0,
    }
