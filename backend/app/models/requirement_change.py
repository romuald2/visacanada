"""RequirementChange model - versioning for requirement modifications."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class RequirementChange(Base):
    __tablename__ = "requirement_changes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("program_requirements.id", ondelete="CASCADE"), nullable=False
    )
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    requirement = relationship("ProgramRequirement", back_populates="changes")
    user = relationship("User", backref="requirement_changes")

    def __repr__(self) -> str:
        return (
            f"<RequirementChange(id={self.id}, requirement_id={self.requirement_id}, "
            f"field={self.field_name})>"
        )
