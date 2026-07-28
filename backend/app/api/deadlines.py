"""Immigration deadlines API (Lot 3).

CRUD for time-sensitive milestones per dossier (ITA response, biometrics,
PPR, permit expiries). The alert engine scans open deadlines and emits
alerts at type-specific thresholds.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.deadline import Deadline, DeadlineSource, DeadlineType
from app.models.dossier import Dossier
from app.models.user import User, UserRole

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


class DeadlineCreate(BaseModel):
    dossier_id: int
    deadline_type: DeadlineType
    due_date: datetime
    description: str | None = None


class DeadlineUpdate(BaseModel):
    deadline_type: DeadlineType | None = None
    due_date: datetime | None = None
    description: str | None = None
    is_completed: bool | None = None


def _serialize(dl: Deadline) -> dict:
    return {
        "id": dl.id,
        "dossier_id": dl.dossier_id,
        "deadline_type": dl.deadline_type.value,
        "due_date": dl.due_date.isoformat() if dl.due_date else None,
        "description": dl.description,
        "source": dl.source.value,
        "is_completed": dl.is_completed,
        "completed_at": dl.completed_at.isoformat() if dl.completed_at else None,
        "created_at": dl.created_at.isoformat() if dl.created_at else None,
    }


def _now_naive() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_deadline(
    body: DeadlineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Create a manual deadline for a dossier."""
    d = await db.execute(select(Dossier).where(Dossier.id == body.dossier_id))
    if d.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Dossier non trouve")

    deadline = Deadline(
        dossier_id=body.dossier_id,
        deadline_type=body.deadline_type,
        due_date=body.due_date,
        description=body.description,
        source=DeadlineSource.manual,
    )
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return _serialize(deadline)


@router.get("")
async def list_deadlines(
    dossier_id: int | None = Query(default=None),
    include_completed: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List deadlines, optionally filtered by dossier."""
    stmt = select(Deadline)
    if dossier_id is not None:
        stmt = stmt.where(Deadline.dossier_id == dossier_id)
    if not include_completed:
        stmt = stmt.where(Deadline.is_completed == False)  # noqa: E712
    stmt = stmt.order_by(Deadline.due_date.asc())

    result = await db.execute(stmt)
    return [_serialize(d) for d in result.scalars().all()]


@router.put("/{deadline_id}")
async def update_deadline(
    deadline_id: int,
    body: DeadlineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Update a deadline (reschedule, edit, or mark complete)."""
    result = await db.execute(select(Deadline).where(Deadline.id == deadline_id))
    deadline = result.scalar_one_or_none()
    if deadline is None:
        raise HTTPException(status_code=404, detail="Echeance non trouvee")

    if body.deadline_type is not None:
        deadline.deadline_type = body.deadline_type
    if body.due_date is not None:
        deadline.due_date = body.due_date
    if body.description is not None:
        deadline.description = body.description
    if body.is_completed is not None:
        deadline.is_completed = body.is_completed
        deadline.completed_at = _now_naive() if body.is_completed else None

    await db.commit()
    await db.refresh(deadline)
    return _serialize(deadline)


@router.post("/{deadline_id}/complete")
async def complete_deadline(
    deadline_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Mark a deadline as completed."""
    result = await db.execute(select(Deadline).where(Deadline.id == deadline_id))
    deadline = result.scalar_one_or_none()
    if deadline is None:
        raise HTTPException(status_code=404, detail="Echeance non trouvee")
    deadline.is_completed = True
    deadline.completed_at = _now_naive()
    await db.commit()
    return {"detail": "Echeance marquee comme terminee"}


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deadline(
    deadline_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Delete a deadline."""
    result = await db.execute(select(Deadline).where(Deadline.id == deadline_id))
    deadline = result.scalar_one_or_none()
    if deadline is None:
        raise HTTPException(status_code=404, detail="Echeance non trouvee")
    await db.delete(deadline)
    await db.commit()
