import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class NotificationType(str, enum.Enum):
    email_ircc = "email_ircc"
    document_missing = "document_missing"
    document_verified = "document_verified"
    document_rejected = "document_rejected"
    deadline_approaching = "deadline_approaching"
    status_change = "status_change"
    policy_update = "policy_update"
    payment_reminder = "payment_reminder"
    system = "system"


class NotificationChannel(str, enum.Enum):
    dashboard = "dashboard"
    whatsapp = "whatsapp"
    email = "email"
    sms = "sms"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    dossier_id: Mapped[int | None] = mapped_column(ForeignKey("dossiers.id"), nullable=True)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), default=NotificationChannel.dashboard, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    recipient = relationship("User", backref="notifications")
    dossier = relationship("Dossier", backref="notifications")

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.notification_type}, read={self.is_read})>"
