from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentStatus, DocumentType


class DocumentCreate(BaseModel):
    dossier_id: int
    document_type: DocumentType
    file_name: str


class DocumentUpdate(BaseModel):
    status: DocumentStatus | None = None
    compliance_score: float | None = None
    fraud_score: float | None = None
    extracted_data: str | None = None
    ai_analysis: str | None = None
    rejection_reason: str | None = None
    expires_at: datetime | None = None


class DocumentResponse(BaseModel):
    id: int
    dossier_id: int
    document_type: DocumentType
    status: DocumentStatus
    file_name: str
    file_path_s3: str | None
    file_size_bytes: int | None
    mime_type: str | None
    compliance_score: float | None
    fraud_score: float | None
    extracted_data: str | None
    ai_analysis: str | None
    rejection_reason: str | None
    expires_at: datetime | None
    uploaded_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentCandidateResponse(BaseModel):
    """Document view for candidates: internal scoring/analysis is withheld.

    compliance_score, fraud_score, extracted_data and ai_analysis are internal
    signals and must never be exposed to the candidate (mirrors the portal).
    """

    id: int
    dossier_id: int
    document_type: DocumentType
    status: DocumentStatus
    file_name: str
    file_size_bytes: int | None
    mime_type: str | None
    rejection_reason: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
