"""API router for document OCR extraction."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus
from app.models.dossier import Dossier
from app.models.user import User, UserRole
from app.services.ocr_service import (
    AzureDocumentIntelligenceService,
    DocumentExtractionType,
    OCRExtractionError,
    azure_ocr_service,
)
from app.services.s3_storage import S3StorageError, s3_storage
from app.services.tesseract_service import tesseract_service

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractionRequest(BaseModel):
    extraction_type: DocumentExtractionType = DocumentExtractionType.generic


class ExtractionDataUpdate(BaseModel):
    extracted_data: dict
    notes: str | None = None


class ExtractionResponse(BaseModel):
    document_id: int
    status: str
    extraction_type: str
    extracted_data: dict | None
    method: str

    model_config = {"from_attributes": True}


@router.post("/{document_id}/extract", response_model=ExtractionResponse)
async def extract_document_data(
    document_id: int,
    request: ExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Trigger OCR extraction on a document.

    Uses Azure Document Intelligence as primary, Tesseract as fallback.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    if not document.file_path_s3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun fichier associé à ce document",
        )

    # Update status to analyzing
    document.status = DocumentStatus.analyzing
    await db.flush()

    # Attempt extraction
    extracted_data = None
    method = "none"

    # Try Azure DI first
    if azure_ocr_service.is_configured:
        try:
            # In production, we'd fetch file from S3
            # For now, we simulate with the stored path
            file_content = await _fetch_file_from_s3(document.file_path_s3)
            extracted_data = await azure_ocr_service.extract_document(
                file_content=file_content,
                mime_type=document.mime_type or "application/pdf",
                extraction_type=request.extraction_type,
            )
            method = "azure_document_intelligence"
        except (OCRExtractionError, S3StorageError):
            # Fall through to Tesseract
            pass

    # Fallback to Tesseract
    if extracted_data is None and tesseract_service.is_available:
        try:
            file_content = await _fetch_file_from_s3(document.file_path_s3)
            extracted_data = await tesseract_service.extract_text(
                file_content=file_content,
                mime_type=document.mime_type or "application/pdf",
            )
            method = "tesseract"
        except OCRExtractionError:
            pass

    # If no extraction method worked
    if extracted_data is None:
        document.status = DocumentStatus.uploaded
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Aucun service OCR disponible. "
                "Configurez Azure Document Intelligence ou installez Tesseract."
            ),
        )

    # Store extracted data
    document.extracted_data = json.dumps(extracted_data, ensure_ascii=False)
    document.status = DocumentStatus.verified
    await db.flush()
    await db.refresh(document)

    return ExtractionResponse(
        document_id=document.id,
        status=document.status.value,
        extraction_type=request.extraction_type.value,
        extracted_data=extracted_data,
        method=method,
    )


@router.get("/{document_id}/extracted-data")
async def get_extracted_data(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the extracted data for a document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    # Check access for candidats
    if current_user.role == UserRole.candidat:
        dossier_result = await db.execute(
            select(Dossier).where(Dossier.id == document.dossier_id)
        )
        dossier = dossier_result.scalar_one_or_none()
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.user_id == current_user.id)
        )
        candidate = candidate_result.scalar_one_or_none()
        if candidate is None or dossier is None or dossier.candidate_id != candidate.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé",
            )

    extracted = None
    if document.extracted_data:
        try:
            extracted = json.loads(document.extracted_data)
        except json.JSONDecodeError:
            extracted = {"raw": document.extracted_data}

    return {
        "document_id": document.id,
        "file_name": document.file_name,
        "document_type": document.document_type,
        "extraction_status": document.status.value,
        "extracted_data": extracted,
    }


@router.put("/{document_id}/extracted-data")
async def update_extracted_data(
    document_id: int,
    data: ExtractionDataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Manually correct OCR extraction results.

    Allows consultants/admins to fix OCR errors.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    # Merge corrections with existing data
    existing_data = {}
    if document.extracted_data:
        try:
            existing_data = json.loads(document.extracted_data)
        except json.JSONDecodeError:
            existing_data = {}

    # Add manual correction metadata
    corrected_data = data.extracted_data
    corrected_data["_manual_correction"] = {
        "corrected_by": current_user.id,
        "corrected_by_name": current_user.full_name,
        "notes": data.notes,
    }

    document.extracted_data = json.dumps(corrected_data, ensure_ascii=False)
    document.status = DocumentStatus.verified
    await db.flush()
    await db.refresh(document)

    return {
        "document_id": document.id,
        "message": "Données corrigées avec succès",
        "extracted_data": corrected_data,
    }


async def _fetch_file_from_s3(s3_key: str) -> bytes:
    """Fetch file content from S3 for OCR processing."""
    try:
        async with s3_storage._session.client("s3", config=s3_storage._config) as s3:
            response = await s3.get_object(
                Bucket=s3_storage._bucket,
                Key=s3_key,
            )
            return await response["Body"].read()
    except Exception as e:
        raise S3StorageError(f"Impossible de récupérer le fichier: {str(e)}")
