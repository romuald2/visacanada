"""CRUD API router for candidates."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateCreate, CandidateResponse, CandidateUpdate

router = APIRouter(prefix="/candidates", tags=["candidates"])


class PaginatedResponse:
    """Helper for paginated list responses."""

    def __init__(self, items: list, total: int, page: int, size: int):
        self.items = items
        self.total = total
        self.page = page
        self.size = size
        self.pages = (total + size - 1) // size if size > 0 else 0


@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Create a new candidate."""
    # Check for duplicate email
    result = await db.execute(
        select(Candidate).where(Candidate.email == data.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un candidat avec cet email existe déjà",
        )

    candidate = Candidate(**data.model_dump())
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


@router.get("/", response_model=dict)
async def list_candidates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    nationality: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List candidates with pagination and optional filters."""
    query = select(Candidate)
    count_query = select(func.count(Candidate.id))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Candidate.first_name.ilike(search_filter))
            | (Candidate.last_name.ilike(search_filter))
            | (Candidate.email.ilike(search_filter))
        )
        count_query = count_query.where(
            (Candidate.first_name.ilike(search_filter))
            | (Candidate.last_name.ilike(search_filter))
            | (Candidate.email.ilike(search_filter))
        )

    if nationality:
        query = query.where(Candidate.nationality == nationality)
        count_query = count_query.where(Candidate.nationality == nationality)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * size
    query = query.order_by(Candidate.created_at.desc()).offset(offset).limit(size)

    result = await db.execute(query)
    candidates = result.scalars().all()

    return {
        "items": [CandidateResponse.model_validate(c) for c in candidates],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size > 0 else 0,
    }


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a candidate by ID."""
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidat non trouvé",
        )

    # Candidats can only view their own profile
    if current_user.role == UserRole.candidat and candidate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé",
        )

    return candidate


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Update a candidate."""
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidat non trouvé",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)

    await db.flush()
    await db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Delete a candidate (admin only)."""
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidat non trouvé",
        )

    await db.delete(candidate)
    await db.flush()
