"""WhatsApp notification models."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class NotificationStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"
    rate_limited = "rate_limited"
    skipped = "skipped"
    not_configured = "not_configured"


class NotificationChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    sms_fallback = "sms_fallback"


class WhatsAppNotification(Base):
    __tablename__ = "whatsapp_notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    to_number: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), nullable=False
    )
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    twilio_sid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", backref="whatsapp_notifications")

    def __repr__(self) -> str:
        return f"<WhatsAppNotification(id={self.id}, event={self.event_type}, status={self.status})>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    whatsapp_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    events: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", backref="notification_preferences")

    def __repr__(self) -> str:
        return f"<NotificationPreference(user_id={self.user_id}, enabled={self.is_enabled})>"
