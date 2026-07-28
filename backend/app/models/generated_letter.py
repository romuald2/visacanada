"""Generated letter model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class GeneratedLetter(Base):
    __tablename__ = "generated_letters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    letter_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    program: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_method: Mapped[str] = mapped_column(String(20), nullable=False)  # ai or template
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_edited: Mapped[bool] = mapped_column(default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    candidate = relationship("Candidate", backref="generated_letters")
    creator = relationship("User", backref="created_letters")

    def __repr__(self) -> str:
        return f"<GeneratedLetter(id={self.id}, type={self.letter_type})>"
