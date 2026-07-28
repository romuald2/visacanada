"""ProgramRequirement model - structured document checklist per program."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class RequirementPriority(str, enum.Enum):
    mandatory = "mandatory"
    recommended = "recommended"
    optional = "optional"


class ProgramRequirement(Base):
    __tablename__ = "program_requirements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[RequirementPriority] = mapped_column(
        Enum(RequirementPriority), default=RequirementPriority.mandatory, nullable=False
    )
    imm_form_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    program = relationship("Program", backref="requirements")
    # Deleting a requirement must delete its change history: requirement_id is
    # NOT NULL, so the default "dissociate" behaviour would violate the FK.
    changes = relationship(
        "RequirementChange",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ProgramRequirement(id={self.id}, program_id={self.program_id}, "
            f"doc={self.document_name}, priority={self.priority})>"
        )
