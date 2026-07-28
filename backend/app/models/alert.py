"""Intelligent alert models: per-dossier config + generated alerts."""

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class AlertType(str, enum.Enum):
    passport_expiring = "passport_expiring"
    medical_expiring = "medical_expiring"
    language_expiring = "language_expiring"
    express_entry_round = "express_entry_round"
    policy_change = "policy_change"
    submission_deadline = "submission_deadline"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertConfig(Base):
    """Per-dossier alert configuration (enable/disable per type)."""

    __tablename__ = "alert_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dossier_id: Mapped[int] = mapped_column(
        ForeignKey("dossiers.id"), unique=True, nullable=False
    )
    # Per-type toggles; missing key = enabled by default
    enabled_types: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Multi-channel toggles: {"dashboard": true, "email": true, "whatsapp": false}
    channels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Alert(Base):
    """A generated alert for a dossier."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity), default=AlertSeverity.info, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Deduplication key so the same condition doesn't re-alert every scan
    dedup_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type}, dossier={self.dossier_id})>"
