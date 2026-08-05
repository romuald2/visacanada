"""API router for secure document upload and access."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus
from app.models.dossier import Dossier
from app.models.user import User, UserRole
from app.schemas.document import DocumentResponse
from app.services.s3_storage import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    S3StorageError,
    s3_storage,
)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/{dossier_id}", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    dossier_id: int,
    document_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document to a dossier.

    Validates file type (PDF, JPG, PNG, DOC, DOCX) and size (max 10MB).
    Stores encrypted on S3 (AES-256) in ca-central-1.
    """
    # Verify dossier exists
    result = await db.execute(select(Dossier).where(Dossier.id == dossier_id))
    dossier = result.scalar_one_or_none()

    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Check access for candidats
    if current_user.role == UserRole.candidat:
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.user_id == current_user.id)
        )
        candidate = candidate_result.scalar_one_or_none()
        if candidate is None or dossier.candidate_id != candidate.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé",
            )

    # Validate MIME type
    mime_type = file.content_type or ""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Type de fichier non autorisé: {mime_type}. "
                f"Formats acceptés: PDF, JPG, PNG, DOC, DOCX"
            ),
        )

    # Read file content and validate size
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Fichier trop volumineux: {file_size / (1024*1024):.1f} MB. "
                f"Maximum: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB"
            ),
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide",
        )

    # Upload to S3
    import io
    file_obj = io.BytesIO(content)

    try:
        upload_result = await s3_storage.upload_file(
            file_content=file_obj,
            candidate_id=dossier.candidate_id,
            dossier_id=dossier_id,
            document_type=document_type,
            original_filename=file.filename or "document",
            mime_type=mime_type,
            file_size=file_size,
        )
    except S3StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Create document record
    document = Document(
        dossier_id=dossier_id,
        document_type=document_type,
        status=DocumentStatus.uploaded,
        file_name=file.filename or "document",
        file_path_s3=upload_result["s3_key"],
        file_size_bytes=file_size,
        mime_type=mime_type,
        uploaded_by=current_user.id,
    )
    db.add(document)

    # Log the upload in audit
    audit = AuditLog(
        user_id=current_user.id,
        action="upload",
        entity_type="document",
        details=f"Upload: {file.filename} ({mime_type}, {file_size} bytes) to dossier {dossier_id}",
    )
    db.add(audit)

    await db.flush()
    await db.refresh(document)
    return document


@router.get("/{document_id}/view")
async def get_document_view_url(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a presigned URL for secure document viewing (inline, no download).

    URL expires after 5 minutes.
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

    if not document.file_path_s3:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non disponible sur le stockage",
        )

    try:
        url = await s3_storage.generate_presigned_url(
            s3_key=document.file_path_s3,
            content_disposition="inline",
        )
    except S3StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Log access
    audit = AuditLog(
        user_id=current_user.id,
        action="view",
        entity_type="document",
        entity_id=document.id,
        details=f"Viewed document: {document.file_name}",
    )
    db.add(audit)
    await db.flush()

    return {"url": url, "expires_in": 300, "content_type": document.mime_type}


@router.get("/{document_id}/download")
async def get_document_download_url(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get a presigned URL for document download (attachment).

    Only admin/consultant can download. URL expires after 5 minutes.
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non disponible sur le stockage",
        )

    try:
        url = await s3_storage.generate_presigned_url(
            s3_key=document.file_path_s3,
            content_disposition=f'attachment; filename="{document.file_name}"',
        )
    except S3StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Log download
    audit = AuditLog(
        user_id=current_user.id,
        action="download",
        entity_type="document",
        entity_id=document.id,
        details=f"Downloaded document: {document.file_name}",
    )
    db.add(audit)
    await db.flush()

    return {"url": url, "expires_in": 300, "filename": document.file_name}


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def soft_delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Soft delete a document (moves to archive on S3, marks as deleted)."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    # Soft delete on S3 if file exists
    archive_key = None
    if document.file_path_s3:
        try:
            archive_key = await s3_storage.soft_delete(document.file_path_s3)
        except S3StorageError:
            # File may not exist on S3 (dev env), continue with DB update
            pass

    # Update document record
    document.status = DocumentStatus.rejected  # Mark as inactive
    document.file_path_s3 = archive_key  # Point to archive location

    # Log deletion
    audit = AuditLog(
        user_id=current_user.id,
        action="soft_delete",
        entity_type="document",
        entity_id=document.id,
        details=f"Soft deleted: {document.file_name} -> archived",
    )
    db.add(audit)
    await db.flush()

    return {
        "message": "Document archivé avec succès",
        "document_id": document_id,
        "archived_path": archive_key,
    }
