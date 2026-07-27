"""EmailConnection model - stores OAuth2 tokens for candidate email access."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class EmailProvider(str, enum.Enum):
    gmail = "gmail"
    outlook = "outlook"


class EmailConnection(Base):
    __tablename__ = "email_connections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider), nullable=False)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consent_given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    consent_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate = relationship("Candidate", backref="email_connections")

    def __repr__(self) -> str:
        return f"<EmailConnection(id={self.id}, provider={self.provider}, email={self.email_address})>"


class IRCCEmail(Base):
    __tablename__ = "ircc_emails"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    dossier_id: Mapped[int | None] = mapped_column(ForeignKey("dossiers.id"), nullable=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("email_connections.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate = relationship("Candidate", backref="ircc_emails")
    dossier = relationship("Dossier", backref="ircc_emails")
    connection = relationship("EmailConnection", backref="emails")

    def __repr__(self) -> str:
        return f"<IRCCEmail(id={self.id}, subject={self.subject[:30]})>"
