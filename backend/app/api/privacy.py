"""Privacy & PIPEDA-compliance API.

Endpoints:
- Consent: record/revoke consent, view my consents, current policy version.
- Data-subject rights: export my data, erase my data.
- Breach register (admin): create/list incidents, mark notification steps.
- Public policy metadata.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.privacy import (
    BreachIncident,
    ConsentRecord,
    ConsentType,
    IncidentSeverity,
    IncidentStatus,
)
from app.models.user import User, UserRole
from app.services.privacy_service import PRIVACY_POLICY_VERSION, privacy_service

router = APIRouter(prefix="/privacy", tags=["privacy"])

_admin_roles = require_role(UserRole.admin)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class ConsentRequest(BaseModel):
    consent_type: str
    granted: bool


class BreachRequest(BaseModel):
    title: str
    description: str
    severity: str
    affected_users_count: int = 0
    sensitive_data: bool = False


class BreachUpdateRequest(BaseModel):
    status: str | None = None
    reported_to_authority: bool | None = None
    users_notified: bool | None = None


# --------------------------------------------------------------------------- #
# Policy metadata (public to authenticated users)
# --------------------------------------------------------------------------- #
@router.get("/policy")
async def get_policy():
    """Return current privacy-policy metadata and consent purposes."""
    return {
        "policy_version": PRIVACY_POLICY_VERSION,
        "consent_types": [
            {
                "type": ct.value,
                "required": ct in (ConsentType.data_processing, ConsentType.document_storage),
            }
            for ct in ConsentType
        ],
    }


# --------------------------------------------------------------------------- #
# Consent
# --------------------------------------------------------------------------- #
@router.post("/consent", status_code=status.HTTP_201_CREATED)
async def record_consent(
    body: ConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record or update the current user's consent for a purpose."""
    try:
        consent_type = ConsentType(body.consent_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Type de consentement invalide: {body.consent_type}"
        )

    # One current record per (user, type, policy_version); update if it exists.
    res = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == current_user.id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.policy_version == PRIVACY_POLICY_VERSION,
        )
    )
    record = res.scalar_one_or_none()
    now = _utcnow()
    if record is None:
        record = ConsentRecord(
            user_id=current_user.id,
            consent_type=consent_type,
            policy_version=PRIVACY_POLICY_VERSION,
        )
        db.add(record)

    record.granted = body.granted
    if body.granted:
        record.granted_at = now
        record.revoked_at = None
    else:
        record.revoked_at = now
    await db.commit()
    await db.refresh(record)

    return {
        "consent_type": consent_type.value,
        "granted": record.granted,
        "policy_version": record.policy_version,
    }


@router.get("/consent")
async def my_consents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's consent records."""
    res = await db.execute(select(ConsentRecord).where(ConsentRecord.user_id == current_user.id))
    records = res.scalars().all()
    return [
        {
            "consent_type": r.consent_type.value
            if hasattr(r.consent_type, "value")
            else r.consent_type,
            "granted": r.granted,
            "policy_version": r.policy_version,
            "granted_at": r.granted_at.isoformat() if r.granted_at else None,
            "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
        }
        for r in records
    ]


# --------------------------------------------------------------------------- #
# Data-subject rights
# --------------------------------------------------------------------------- #
@router.get("/my-data")
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Right of access / portability: export all personal data held about me."""
    return await privacy_service.export_user_data(current_user, db)


@router.delete("/my-data")
async def erase_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Right to erasure: delete/anonymize my personal data."""
    return await privacy_service.erase_user_data(current_user, db)


# --------------------------------------------------------------------------- #
# Breach register (admin only)
# --------------------------------------------------------------------------- #
@router.post("/breaches", status_code=status.HTTP_201_CREATED)
async def report_breach(
    body: BreachRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
):
    """Register a security-breach incident and assess notification duty."""
    try:
        severity = IncidentSeverity(body.severity)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Gravite invalide: {body.severity}")

    requires_notification = privacy_service.assess_breach_notification(
        severity.value, body.affected_users_count, body.sensitive_data
    )
    incident = BreachIncident(
        title=body.title,
        description=body.description,
        severity=severity,
        status=IncidentStatus.open,
        affected_users_count=body.affected_users_count,
        requires_notification=requires_notification,
        reported_by=current_user.id,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return {
        "id": incident.id,
        "title": incident.title,
        "severity": incident.severity.value
        if hasattr(incident.severity, "value")
        else incident.severity,
        "status": incident.status.value if hasattr(incident.status, "value") else incident.status,
        "requires_notification": incident.requires_notification,
    }


@router.get("/breaches")
async def list_breaches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
):
    """List breach incidents (most recent first)."""
    res = await db.execute(select(BreachIncident).order_by(BreachIncident.detected_at.desc()))
    incidents = res.scalars().all()
    return [
        {
            "id": i.id,
            "title": i.title,
            "severity": i.severity.value if hasattr(i.severity, "value") else i.severity,
            "status": i.status.value if hasattr(i.status, "value") else i.status,
            "affected_users_count": i.affected_users_count,
            "requires_notification": i.requires_notification,
            "reported_to_authority": i.reported_to_authority,
            "users_notified": i.users_notified,
            "detected_at": i.detected_at.isoformat() if i.detected_at else None,
        }
        for i in incidents
    ]


@router.put("/breaches/{incident_id}")
async def update_breach(
    incident_id: int,
    body: BreachUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
):
    """Update an incident's status and notification tracking."""
    res = await db.execute(select(BreachIncident).where(BreachIncident.id == incident_id))
    incident = res.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident non trouve")

    if body.status is not None:
        try:
            incident.status = IncidentStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {body.status}")
        if incident.status == IncidentStatus.resolved:
            incident.resolved_at = _utcnow()
    if body.reported_to_authority is not None:
        incident.reported_to_authority = body.reported_to_authority
    if body.users_notified is not None:
        incident.users_notified = body.users_notified
    await db.commit()
    await db.refresh(incident)
    return {
        "id": incident.id,
        "status": incident.status.value if hasattr(incident.status, "value") else incident.status,
        "reported_to_authority": incident.reported_to_authority,
        "users_notified": incident.users_notified,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }
