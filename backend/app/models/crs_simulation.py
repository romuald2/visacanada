"""CRS Simulation model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class CRSSimulation(Base):
    __tablename__ = "crs_simulations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    calculated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate = relationship("Candidate", backref="crs_simulations")
    calculator = relationship("User", backref="crs_calculations")

    def __repr__(self) -> str:
        return f"<CRSSimulation(id={self.id}, score={self.total_score})>"
