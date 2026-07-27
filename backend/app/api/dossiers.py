"""CRUD API router for dossiers."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.dossier import Dossier, DossierStatus
from app.models.program import Program
from app.models.user import User, UserRole
from app.schemas.dossier import DossierCreate, DossierResponse, DossierUpdate

router = APIRouter(prefix="/dossiers", tags=["dossiers"])


@router.post("/", response_model=DossierResponse, status_code=status.HTTP_201_CREATED)
async def create_dossier(
    data: DossierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Create a new dossier for a candidate."""
    # Verify candidate exists
    result = await db.execute(
        select(Candidate).where(Candidate.id == data.candidate_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidat non trouvé",
        )

    # Verify program exists
    result = await db.execute(
        select(Program).where(Program.id == data.program_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programme non trouvé",
        )

    dossier = Dossier(
        **data.model_dump(),
        status=DossierStatus.nouveau,
    )
    db.add(dossier)
    await db.flush()
    await db.refresh(dossier)
    return dossier


@router.get("/", response_model=dict)
async def list_dossiers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: DossierStatus | None = Query(None, alias="status"),
    program_id: int | None = None,
    candidate_id: int | None = None,
    assigned_to: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List dossiers with pagination and filters."""
    query = select(Dossier)
    count_query = select(func.count(Dossier.id))

    # Role-based filtering: candidats only see their own dossiers
    if current_user.role == UserRole.candidat:
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.user_id == current_user.id)
        )
        candidate = candidate_result.scalar_one_or_none()
        if candidate is None:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}
        query = query.where(Dossier.candidate_id == candidate.id)
        count_query = count_query.where(Dossier.candidate_id == candidate.id)

    if status_filter:
        query = query.where(Dossier.status == status_filter)
        count_query = count_query.where(Dossier.status == status_filter)

    if program_id:
        query = query.where(Dossier.program_id == program_id)
        count_query = count_query.where(Dossier.program_id == program_id)

    if candidate_id:
        query = query.where(Dossier.candidate_id == candidate_id)
        count_query = count_query.where(Dossier.candidate_id == candidate_id)

    if assigned_to:
        query = query.where(Dossier.assigned_to == assigned_to)
        count_query = count_query.where(Dossier.assigned_to == assigned_to)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * size
    query = query.order_by(Dossier.created_at.desc()).offset(offset).limit(size)

    result = await db.execute(query)
    dossiers = result.scalars().all()

    return {
        "items": [DossierResponse.model_validate(d) for d in dossiers],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size > 0 else 0,
    }


@router.get("/{dossier_id}", response_model=DossierResponse)
async def get_dossier(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a dossier by ID."""
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()

    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Candidats can only view their own dossiers
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

    return dossier


@router.put("/{dossier_id}", response_model=DossierResponse)
async def update_dossier(
    dossier_id: int,
    data: DossierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Update a dossier."""
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()

    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Handle status transition timestamps
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == DossierStatus.soumis and dossier.submitted_at is None:
            dossier.submitted_at = datetime.now()
        if new_status in (DossierStatus.approuve, DossierStatus.refuse):
            dossier.decision_at = datetime.now()

    for field, value in update_data.items():
        setattr(dossier, field, value)

    await db.flush()
    await db.refresh(dossier)
    return dossier


@router.delete("/{dossier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dossier(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Delete a dossier (admin only)."""
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()

    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    await db.delete(dossier)
    await db.flush()
