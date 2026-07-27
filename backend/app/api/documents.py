"""CRUD API router for documents."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus
from app.models.dossier import Dossier
from app.models.user import User, UserRole
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a document record (metadata only, upload handled separately)."""
    # Verify dossier exists
    result = await db.execute(
        select(Dossier).where(Dossier.id == data.dossier_id)
    )
    dossier = result.scalar_one_or_none()

    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Candidats can only add documents to their own dossiers
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

    document = Document(
        **data.model_dump(),
        status=DocumentStatus.pending,
        uploaded_by=current_user.id,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


@router.get("/", response_model=dict)
async def list_documents(
    dossier_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: DocumentStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents for a dossier."""
    # Verify dossier exists and user has access
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()

    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Candidats can only view documents for their own dossiers
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

    query = select(Document).where(Document.dossier_id == dossier_id)
    count_query = select(func.count(Document.id)).where(Document.dossier_id == dossier_id)

    if status_filter:
        query = query.where(Document.status == status_filter)
        count_query = count_query.where(Document.status == status_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * size
    query = query.order_by(Document.created_at.desc()).offset(offset).limit(size)

    result = await db.execute(query)
    documents = result.scalars().all()

    return {
        "items": [DocumentResponse.model_validate(d) for d in documents],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size > 0 else 0,
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a document by ID."""
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

    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Update a document (status, scores, analysis)."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    await db.flush()
    await db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Delete a document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    await db.delete(document)
    await db.flush()
