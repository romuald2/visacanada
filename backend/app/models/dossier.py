import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class DossierStatus(str, enum.Enum):
    nouveau = "nouveau"
    en_cours = "en_cours"
    documents_manquants = "documents_manquants"
    en_revision = "en_revision"
    soumis = "soumis"
    approuve = "approuve"
    refuse = "refuse"
    archive = "archive"


class Dossier(Base):
    __tablename__ = "dossiers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[DossierStatus] = mapped_column(
        Enum(DossierStatus), default=DossierStatus.nouveau, nullable=False
    )
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    candidate = relationship("Candidate", back_populates="dossiers")
    program = relationship("Program", back_populates="dossiers")
    assigned_user = relationship("User", backref="assigned_dossiers")
    documents = relationship("Document", back_populates="dossier")

    def __repr__(self) -> str:
        return f"<Dossier(id={self.id}, status={self.status}, score={self.compliance_score})>"
