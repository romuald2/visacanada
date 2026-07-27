import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class DocumentType(str, enum.Enum):
    passport = "passport"
    birth_certificate = "birth_certificate"
    photo = "photo"
    language_test = "language_test"
    education_credential = "education_credential"
    work_reference = "work_reference"
    bank_statement = "bank_statement"
    police_certificate = "police_certificate"
    medical_exam = "medical_exam"
    travel_history = "travel_history"
    employment_letter = "employment_letter"
    invitation_letter = "invitation_letter"
    proof_of_funds = "proof_of_funds"
    marriage_certificate = "marriage_certificate"
    cv_resume = "cv_resume"
    cover_letter = "cover_letter"
    other = "other"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    uploaded = "uploaded"
    analyzing = "analyzing"
    verified = "verified"
    rejected = "rejected"
    expired = "expired"
    fraud_suspected = "fraud_suspected"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.pending, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_s3: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fraud_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extracted_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    dossier = relationship("Dossier", back_populates="documents")
    uploader = relationship("User", backref="uploaded_documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, type={self.document_type}, status={self.status})>"
