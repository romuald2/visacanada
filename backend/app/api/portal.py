"""Candidate self-service portal API (read-only + self-upload).

Scoped strictly to the authenticated candidat's own dossiers.
Never exposes internal scores (compliance/fraud), AI analysis, or admin tools.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus
from app.models.dossier import Dossier, DossierStatus
from app.models.notification import Notification
from app.models.program import Program
from app.models.program_requirement import ProgramRequirement
from app.models.user import User, UserRole
from app.services.s3_storage import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    S3StorageError,
    s3_storage,
)

router = APIRouter(prefix="/portal", tags=["portal"])


# Progression percentage per dossier status (visual progress bar)
STATUS_PROGRESS = {
    DossierStatus.nouveau: 10,
    DossierStatus.en_cours: 30,
    DossierStatus.documents_manquants: 40,
    DossierStatus.en_revision: 70,
    DossierStatus.soumis: 90,
    DossierStatus.approuve: 100,
    DossierStatus.refuse: 100,
    DossierStatus.archive: 100,
}

# Bilingual status labels (FR / EN)
STATUS_LABELS = {
    DossierStatus.nouveau: {"fr": "Nouveau", "en": "New"},
    DossierStatus.en_cours: {"fr": "En cours", "en": "In progress"},
    DossierStatus.documents_manquants: {
        "fr": "Documents manquants",
        "en": "Missing documents",
    },
    DossierStatus.en_revision: {"fr": "En revision", "en": "Under review"},
    DossierStatus.soumis: {"fr": "Soumis", "en": "Submitted"},
    DossierStatus.approuve: {"fr": "Approuve", "en": "Approved"},
    DossierStatus.refuse: {"fr": "Refuse", "en": "Refused"},
    DossierStatus.archive: {"fr": "Archive", "en": "Archived"},
}


async def get_current_candidate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    """Resolve the Candidate record owned by the authenticated candidat user.

    Enforces that only candidat-role users access the portal, and that they
    only ever reach their own candidate profile.
    """
    if current_user.role != UserRole.candidat:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portail reserve aux candidats",
        )

    result = await db.execute(
        select(Candidate).where(Candidate.user_id == current_user.id)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun profil candidat associe a ce compte",
        )
    return candidate


async def _get_owned_dossier(
    dossier_id: int, candidate: Candidate, db: AsyncSession
) -> Dossier:
    """Fetch a dossier only if it belongs to this candidate."""
    result = await db.execute(
        select(Dossier).where(
            Dossier.id == dossier_id,
            Dossier.candidate_id == candidate.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouve",
        )
    return dossier


@router.get("/me")
async def get_my_profile(
    candidate: Candidate = Depends(get_current_candidate),
):
    """Candidate's own profile summary."""
    return {
        "id": candidate.id,
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "nationality": candidate.nationality,
    }


@router.get("/dossiers")
async def list_my_dossiers(
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    """List the candidate's own dossiers with visual progression.

    Internal scores (compliance/fraud) are never included.
    """
    result = await db.execute(
        select(Dossier).where(Dossier.candidate_id == candidate.id)
    )
    dossiers = result.scalars().all()

    items = []
    for d in dossiers:
        items.append(
            {
                "id": d.id,
                "status": d.status.value,
                "status_label": STATUS_LABELS.get(d.status, {}),
                "progress": STATUS_PROGRESS.get(d.status, 0),
                "reference_number": d.reference_number,
                "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
        )
    return items


@router.get("/dossiers/{dossier_id}")
async def get_my_dossier(
    dossier_id: int,
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    """Detailed view of a single owned dossier (read-only, no internal scores)."""
    dossier = await _get_owned_dossier(dossier_id, candidate, db)

    prog = await db.execute(select(Program).where(Program.id == dossier.program_id))
    program = prog.scalar_one_or_none()

    return {
        "id": dossier.id,
        "status": dossier.status.value,
        "status_label": STATUS_LABELS.get(dossier.status, {}),
        "progress": STATUS_PROGRESS.get(dossier.status, 0),
        "reference_number": dossier.reference_number,
        "program": {
            "id": program.id,
            "name": program.name,
            "category": program.category,
        }
        if program
        else None,
        "submitted_at": dossier.submitted_at.isoformat()
        if dossier.submitted_at
        else None,
        "decision_at": dossier.decision_at.isoformat()
        if dossier.decision_at
        else None,
        "created_at": dossier.created_at.isoformat() if dossier.created_at else None,
        "updated_at": dossier.updated_at.isoformat() if dossier.updated_at else None,
    }


@router.get("/dossiers/{dossier_id}/documents")
async def get_my_documents(
    dossier_id: int,
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    """Documents provided vs missing for an owned dossier.

    Exposes only candidate-safe fields — no compliance/fraud scores or AI analysis.
    """
    dossier = await _get_owned_dossier(dossier_id, candidate, db)

    # Provided documents
    doc_result = await db.execute(
        select(Document).where(Document.dossier_id == dossier.id)
    )
    documents = doc_result.scalars().all()
    provided = [
        {
            "id": doc.id,
            "document_type": doc.document_type.value,
            "file_name": doc.file_name,
            "status": doc.status.value,
            "rejection_reason": doc.rejection_reason
            if doc.status == DocumentStatus.rejected
            else None,
            "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in documents
    ]
    provided_types = {doc.document_type.value for doc in documents}

    # Required documents for the program
    req_result = await db.execute(
        select(ProgramRequirement).where(
            ProgramRequirement.program_id == dossier.program_id,
            ProgramRequirement.is_active == True,  # noqa: E712
        )
    )
    requirements = req_result.scalars().all()
    missing = [
        {
            "document_type": req.document_type,
            "document_name": req.document_name,
            "description": req.description,
            "priority": req.priority.value,
        }
        for req in requirements
        if req.document_type not in provided_types
    ]

    return {
        "dossier_id": dossier.id,
        "provided": provided,
        "missing": missing,
        "provided_count": len(provided),
        "missing_count": len(missing),
    }


@router.get("/notifications")
async def get_my_notifications(
    candidate: Candidate = Depends(get_current_candidate),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Progression notifications addressed to the candidate."""
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "type": n.notification_type.value,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    candidate: Candidate = Depends(get_current_candidate),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark one of the candidate's own notifications as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvee",
        )
    notification.is_read = True
    await db.commit()
    return {"detail": "Notification marquee comme lue"}


@router.post("/dossiers/{dossier_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_my_document(
    dossier_id: int,
    document_type: str,
    file: UploadFile = File(...),
    candidate: Candidate = Depends(get_current_candidate),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Candidate uploads a document to their own dossier.

    Ownership is enforced via get_current_candidate + owned-dossier check.
    """
    import io

    dossier = await _get_owned_dossier(dossier_id, candidate, db)

    mime_type = file.content_type or ""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Type de fichier non autorise: {mime_type}. "
                f"Formats acceptes: PDF, JPG, PNG, DOC, DOCX"
            ),
        )

    content = await file.read()
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide",
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Fichier trop volumineux: {file_size / (1024*1024):.1f} MB. "
                f"Maximum: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB"
            ),
        )

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

    audit = AuditLog(
        user_id=current_user.id,
        action="upload",
        entity_type="document",
        details=f"Portal upload: {file.filename} to dossier {dossier_id}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(document)

    return {
        "id": document.id,
        "document_type": document.document_type.value,
        "file_name": document.file_name,
        "status": document.status.value,
        "uploaded_at": document.created_at.isoformat()
        if document.created_at
        else None,
    }
