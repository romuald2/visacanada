"""Intelligent alerts API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.alert import Alert, AlertConfig
from app.models.dossier import Dossier
from app.models.user import User, UserRole
from app.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertConfigUpdate(BaseModel):
    enabled_types: dict[str, bool] | None = None
    channels: dict[str, bool] | None = None
    is_enabled: bool | None = None


@router.post("/scan")
async def run_scan(
    deliver: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Trigger a scan of all active dossiers for alert conditions.

    When ``deliver`` is true (default) newly-created alerts are also
    dispatched across each dossier's configured channels.
    """
    if deliver:
        stats = await alert_service.scan_and_deliver(db)
        return {"detail": "Scan termine", **stats}
    count = await alert_service.scan_all(db)
    return {"detail": "Scan termine", "new_alerts": count}


@router.get("")
async def list_alerts(
    dossier_id: int | None = Query(default=None),
    include_dismissed: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List alerts, optionally filtered by dossier."""
    stmt = select(Alert)
    if dossier_id is not None:
        stmt = stmt.where(Alert.dossier_id == dossier_id)
    if not include_dismissed:
        stmt = stmt.where(Alert.is_dismissed == False)  # noqa: E712
    stmt = stmt.order_by(Alert.created_at.desc())

    result = await db.execute(stmt)
    alerts = result.scalars().all()
    return [
        {
            "id": a.id,
            "dossier_id": a.dossier_id,
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "title": a.title,
            "message": a.message,
            "is_dismissed": a.is_dismissed,
            "is_notified": a.is_notified,
            "extra_data": a.extra_data,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.get("/upcoming")
async def upcoming_alerts(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Aggregated view of active deadlines/alerts, most urgent first.

    Sorts by severity (critical → warning → info) then by how soon the
    condition fires (``days_left`` from the alert payload).
    """
    stmt = (
        select(Alert)
        .where(Alert.is_dismissed == False)  # noqa: E712
        .order_by(Alert.created_at.desc())
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    severity_rank = {"critical": 0, "warning": 1, "info": 2}

    def _days_left(a: Alert) -> int:
        val = (a.extra_data or {}).get("days_left")
        return val if isinstance(val, int) else 10**6

    items = [
        {
            "id": a.id,
            "dossier_id": a.dossier_id,
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "title": a.title,
            "message": a.message,
            "days_left": (a.extra_data or {}).get("days_left"),
            "is_notified": a.is_notified,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
        if _days_left(a) <= days
    ]
    items.sort(
        key=lambda i: (
            severity_rank.get(i["severity"], 3),
            i["days_left"] if isinstance(i["days_left"], int) else 10**6,
        )
    )
    return {"count": len(items), "window_days": days, "items": items}


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Dismiss an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerte non trouvee")
    alert.is_dismissed = True
    await db.commit()
    return {"detail": "Alerte ignoree"}


@router.get("/config/{dossier_id}")
async def get_config(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get alert configuration for a dossier (defaults if none set)."""
    result = await db.execute(
        select(AlertConfig).where(AlertConfig.dossier_id == dossier_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        return {
            "dossier_id": dossier_id,
            "is_enabled": True,
            "enabled_types": {},
            "channels": {"dashboard": True, "email": True, "whatsapp": False},
        }
    return {
        "dossier_id": config.dossier_id,
        "is_enabled": config.is_enabled,
        "enabled_types": config.enabled_types or {},
        "channels": config.channels
        or {"dashboard": True, "email": True, "whatsapp": False},
    }


@router.put("/config/{dossier_id}")
async def update_config(
    dossier_id: int,
    body: AlertConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Create or update per-dossier alert configuration."""
    # Verify dossier exists
    d = await db.execute(select(Dossier).where(Dossier.id == dossier_id))
    if d.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Dossier non trouve")

    result = await db.execute(
        select(AlertConfig).where(AlertConfig.dossier_id == dossier_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = AlertConfig(dossier_id=dossier_id)
        db.add(config)

    if body.enabled_types is not None:
        config.enabled_types = body.enabled_types
    if body.channels is not None:
        config.channels = body.channels
    if body.is_enabled is not None:
        config.is_enabled = body.is_enabled

    await db.commit()
    await db.refresh(config)
    return {
        "dossier_id": config.dossier_id,
        "is_enabled": config.is_enabled,
        "enabled_types": config.enabled_types or {},
        "channels": config.channels or {},
    }
