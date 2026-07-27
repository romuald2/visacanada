"""FraudAlert model - stores fraud detection results for documents."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class FraudRiskLevel(str, enum.Enum):
    negligible = "negligible"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FraudAlertStatus(str, enum.Enum):
    pending_review = "pending_review"
    reviewed_legitimate = "reviewed_legitimate"
    reviewed_suspicious = "reviewed_suspicious"
    reviewed_fraudulent = "reviewed_fraudulent"


class FraudAnalysis(Base):
    __tablename__ = "fraud_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    fraud_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[FraudRiskLevel] = mapped_column(
        Enum(FraudRiskLevel), default=FraudRiskLevel.negligible, nullable=False
    )
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alerts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    alerts_count: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FraudAlertStatus] = mapped_column(
        Enum(FraudAlertStatus), default=FraudAlertStatus.pending_review, nullable=False
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document = relationship("Document", backref="fraud_analyses")
    reviewer = relationship("User", backref="fraud_reviews")

    def __repr__(self) -> str:
        return (
            f"<FraudAnalysis(id={self.id}, doc={self.document_id}, "
            f"score={self.fraud_score}, risk={self.risk_level})>"
        )
