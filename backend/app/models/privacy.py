"""PIPEDA compliance models: consent records and breach incidents.

Supports the privacy obligations required before production:
- Explicit, versioned, revocable consent (PIPEDA principle 3).
- Security-breach incident register with notification tracking
  (PIPEDA breach-of-security-safeguards reporting).
Data access/erasure rights are served from the API using existing models.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConsentType(str, Enum):
    data_processing = "data_processing"
    document_storage = "document_storage"
    ai_analysis = "ai_analysis"
    marketing = "marketing"
    third_party_sharing = "third_party_sharing"


class IncidentSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    contained = "contained"
    resolved = "resolved"


class ConsentRecord(Base):
    """A user's consent decision for a specific purpose, versioned and revocable."""

    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    consent_type: Mapped[ConsentType] = mapped_column(String(50), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


class BreachIncident(Base):
    """A security-breach incident record with notification tracking."""

    __tablename__ = "breach_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(String(20), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        String(20), default=IncidentStatus.open, nullable=False
    )
    affected_users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Real risk of significant harm -> mandatory notification under PIPEDA.
    requires_notification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reported_to_authority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    users_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reported_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
