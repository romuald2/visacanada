"""API router for programs and requirements (IRCC knowledge base)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.program import Program
from app.models.program_requirement import ProgramRequirement
from app.models.requirement_change import RequirementChange
from app.models.user import User, UserRole
from app.schemas.requirement import (
    ProgramListResponse,
    ProgramRequirementCreate,
    ProgramRequirementResponse,
    ProgramRequirementUpdate,
    RequirementChangeResponse,
)

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("/", response_model=list[ProgramListResponse])
async def list_programs(
    category: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all immigration programs."""
    query = select(Program)

    if active_only:
        query = query.where(Program.is_active == True)

    if category:
        query = query.where(Program.category == category)

    query = query.order_by(Program.category, Program.name)
    result = await db.execute(query)
    programs = result.scalars().all()

    return [ProgramListResponse.model_validate(p) for p in programs]


@router.get("/{program_id}", response_model=ProgramListResponse)
async def get_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single program by ID."""
    result = await db.execute(select(Program).where(Program.id == program_id))
    program = result.scalar_one_or_none()

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programme non trouvé",
        )

    return program


@router.get("/{program_id}/requirements", response_model=list[ProgramRequirementResponse])
async def get_program_requirements(
    program_id: int,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the document checklist for a specific program."""
    # Verify program exists
    result = await db.execute(select(Program).where(Program.id == program_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programme non trouvé",
        )

    query = select(ProgramRequirement).where(
        ProgramRequirement.program_id == program_id
    )

    if active_only:
        query = query.where(ProgramRequirement.is_active == True)

    query = query.order_by(ProgramRequirement.sort_order, ProgramRequirement.document_name)
    result = await db.execute(query)
    requirements = result.scalars().all()

    return [ProgramRequirementResponse.model_validate(r) for r in requirements]


@router.post(
    "/{program_id}/requirements",
    response_model=ProgramRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement(
    program_id: int,
    data: ProgramRequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Add a requirement to a program (admin only)."""
    # Verify program exists
    result = await db.execute(select(Program).where(Program.id == program_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programme non trouvé",
        )

    requirement = ProgramRequirement(
        program_id=program_id,
        document_type=data.document_type,
        document_name=data.document_name,
        description=data.description,
        priority=data.priority,
        imm_form_reference=data.imm_form_reference,
        sort_order=data.sort_order,
        notes=data.notes,
    )
    db.add(requirement)
    await db.flush()
    await db.refresh(requirement)

    # Log creation in change history
    change = RequirementChange(
        requirement_id=requirement.id,
        changed_by=current_user.id,
        field_name="*",
        old_value=None,
        new_value=f"Created: {data.document_name}",
        reason="Création initiale",
    )
    db.add(change)
    await db.flush()

    return requirement


@router.put(
    "/requirements/{requirement_id}",
    response_model=ProgramRequirementResponse,
)
async def update_requirement(
    requirement_id: int,
    data: ProgramRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Update a requirement (admin only). Changes are versioned."""
    result = await db.execute(
        select(ProgramRequirement).where(ProgramRequirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()

    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exigence non trouvée",
        )

    update_data = data.model_dump(exclude_unset=True)
    change_reason = update_data.pop("change_reason", None)

    # Track changes
    for field, new_value in update_data.items():
        old_value = getattr(requirement, field)
        if str(old_value) != str(new_value):
            change = RequirementChange(
                requirement_id=requirement.id,
                changed_by=current_user.id,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                reason=change_reason,
            )
            db.add(change)

    # Apply updates
    for field, value in update_data.items():
        setattr(requirement, field, value)

    await db.flush()
    await db.refresh(requirement)
    return requirement


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Delete a requirement (admin only)."""
    result = await db.execute(
        select(ProgramRequirement).where(ProgramRequirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()

    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exigence non trouvée",
        )

    await db.delete(requirement)
    await db.flush()


@router.get(
    "/requirements/{requirement_id}/history",
    response_model=list[RequirementChangeResponse],
)
async def get_requirement_history(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get the change history for a requirement."""
    # Verify requirement exists
    result = await db.execute(
        select(ProgramRequirement).where(ProgramRequirement.id == requirement_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exigence non trouvée",
        )

    query = (
        select(RequirementChange)
        .where(RequirementChange.requirement_id == requirement_id)
        .order_by(RequirementChange.created_at.desc())
    )
    result = await db.execute(query)
    changes = result.scalars().all()

    return [RequirementChangeResponse.model_validate(c) for c in changes]
