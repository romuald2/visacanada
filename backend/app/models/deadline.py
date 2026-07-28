"""Immigration deadline model.

Tracks time-sensitive milestones that are NOT documents: an ITA response
window (60 days to submit an e-APR), biometrics collection (30 days after
the request letter), a PPR / passport request, a medical request, and
permit expiries. The alert engine scans open deadlines and emits alerts at
type-specific thresholds.
"""

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class DeadlineType(str, enum.Enum):
    ita_response = "ita_response"          # Invitation to Apply — 60 days to submit
    biometrics = "biometrics"              # Biometrics collection — 30 days
    ppr = "ppr"                            # Passport request / final documents
    medical_request = "medical_request"    # Requested medical exam
    submission = "submission"              # Generic dossier submission deadline
    work_permit_expiry = "work_permit_expiry"
    study_permit_expiry = "study_permit_expiry"
    custom = "custom"


class DeadlineSource(str, enum.Enum):
    manual = "manual"      # Entered by a consultant
    derived = "derived"    # Derived from an event (e.g. ITA date)


class Deadline(Base):
    """A time-sensitive milestone attached to a dossier."""

    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dossier_id: Mapped[int] = mapped_column(
        ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deadline_type: Mapped[DeadlineType] = mapped_column(
        Enum(DeadlineType), nullable=False
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[DeadlineSource] = mapped_column(
        Enum(DeadlineSource), default=DeadlineSource.manual, nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dossier = relationship("Dossier", backref="deadlines")

    def __repr__(self) -> str:
        return (
            f"<Deadline(id={self.id}, type={self.deadline_type}, "
            f"due={self.due_date}, done={self.is_completed})>"
        )
