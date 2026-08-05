"""Complaint model for PIPEDA Principle 10 (contestation)."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class Complaint(Base):
    """User complaint regarding personal data handling."""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50), default="nouveau"
    )  # nouveau, en_cours, resolu, rejete
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="complaints")
