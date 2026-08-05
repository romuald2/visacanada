"""API router for IRCC updates and monitoring."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.ircc_update import IRCCUpdate, IRCCUpdateCategory
from app.models.user import User, UserRole
from app.services.ircc_monitor import IRCCFeedParser
from app.tasks.ircc_tasks import _notify_admins, _store_new_updates

router = APIRouter(prefix="/ircc", tags=["ircc-monitoring"])


class IRCCUpdateOut(BaseModel):
    id: int
    title: str
    content: str | None
    summary: str | None
    category: IRCCUpdateCategory
    source: str
    source_url: str | None
    is_read: bool
    is_notified: bool
    published_at: datetime | None
    detected_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/updates", response_model=dict)
async def list_updates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: IRCCUpdateCategory | None = None,
    is_read: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List IRCC updates with pagination and filters."""
    query = select(IRCCUpdate)
    count_query = select(func.count(IRCCUpdate.id))

    if category:
        query = query.where(IRCCUpdate.category == category)
        count_query = count_query.where(IRCCUpdate.category == category)

    if is_read is not None:
        query = query.where(IRCCUpdate.is_read == is_read)
        count_query = count_query.where(IRCCUpdate.is_read == is_read)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * size
    query = query.order_by(IRCCUpdate.detected_at.desc()).offset(offset).limit(size)

    result = await db.execute(query)
    updates = result.scalars().all()

    return {
        "items": [IRCCUpdateOut.model_validate(u) for u in updates],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size > 0 else 0,
    }


@router.get("/updates/{update_id}", response_model=IRCCUpdateOut)
async def get_update(
    update_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get a single IRCC update by ID."""
    result = await db.execute(
        select(IRCCUpdate).where(IRCCUpdate.id == update_id)
    )
    update = result.scalar_one_or_none()

    if update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mise à jour non trouvée",
        )

    # Mark as read
    if not update.is_read:
        update.is_read = True
        await db.flush()

    return update


@router.post("/updates/{update_id}/read", response_model=IRCCUpdateOut)
async def mark_as_read(
    update_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Mark an IRCC update as read."""
    result = await db.execute(
        select(IRCCUpdate).where(IRCCUpdate.id == update_id)
    )
    update = result.scalar_one_or_none()

    if update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mise à jour non trouvée",
        )

    update.is_read = True
    await db.flush()
    await db.refresh(update)
    return update


@router.post("/updates/refresh", response_model=dict)
async def refresh_updates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Manually trigger IRCC feed refresh (admin only)."""
    parser = IRCCFeedParser()

    try:
        updates = await parser.fetch_all_sources()
        new_updates = await _store_new_updates(db, updates)
        notified = 0

        if new_updates:
            notified = await _notify_admins(db, new_updates)

        await db.commit()

        return {
            "fetched": len(updates),
            "new": len(new_updates),
            "notified": notified,
            "message": f"{len(new_updates)} nouvelle(s) mise(s) à jour détectée(s)",
        }
    finally:
        await parser.close()


@router.get("/stats", response_model=dict)
async def get_monitoring_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get IRCC monitoring statistics."""
    total_result = await db.execute(select(func.count(IRCCUpdate.id)))
    total = total_result.scalar()

    unread_result = await db.execute(
        select(func.count(IRCCUpdate.id)).where(IRCCUpdate.is_read == False)  # noqa: E712
    )
    unread = unread_result.scalar()

    # Count by category
    categories = {}
    for cat in IRCCUpdateCategory:
        cat_result = await db.execute(
            select(func.count(IRCCUpdate.id)).where(IRCCUpdate.category == cat)
        )
        count = cat_result.scalar()
        if count > 0:
            categories[cat.value] = count

    return {
        "total_updates": total,
        "unread": unread,
        "by_category": categories,
    }
