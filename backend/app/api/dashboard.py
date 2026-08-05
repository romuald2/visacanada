"""Admin dashboard API router."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus
from app.models.dossier import Dossier, DossierStatus
from app.models.program import Program
from app.models.user import User, UserRole
from app.models.whatsapp_notification import WhatsAppNotification

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get dossier counts by status for overview cards/charts."""
    # Count dossiers per status
    result = await db.execute(
        select(Dossier.status, func.count(Dossier.id)).group_by(Dossier.status)
    )
    status_counts = {
        row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in result.all()
    }

    # Total dossiers
    total_result = await db.execute(select(func.count(Dossier.id)))
    total = total_result.scalar() or 0

    # Total candidates
    candidates_result = await db.execute(select(func.count(Candidate.id)))
    total_candidates = candidates_result.scalar() or 0

    # Average compliance score (non-null only)
    avg_score_result = await db.execute(
        select(func.avg(Dossier.compliance_score)).where(Dossier.compliance_score.isnot(None))
    )
    avg_score = avg_score_result.scalar()

    return {
        "total_dossiers": total,
        "total_candidates": total_candidates,
        "average_compliance_score": round(avg_score, 1) if avg_score else None,
        "by_status": status_counts,
    }


@router.get("/urgent-actions")
async def get_urgent_actions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get urgent actions: expiring documents, approaching deadlines."""
    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)
    in_30_days = now_naive + timedelta(days=30)

    # Documents expiring within 30 days
    expiring_docs_result = await db.execute(
        select(Document)
        .where(
            Document.expires_at.isnot(None),
            Document.expires_at <= in_30_days,
            Document.expires_at > now_naive,
            Document.status != DocumentStatus.expired,
        )
        .order_by(Document.expires_at.asc())
        .limit(20)
    )
    expiring_docs = expiring_docs_result.scalars().all()

    # Already expired documents (not yet marked)
    expired_docs_result = await db.execute(
        select(Document)
        .where(
            Document.expires_at.isnot(None),
            Document.expires_at <= now_naive,
            Document.status != DocumentStatus.expired,
        )
        .order_by(Document.expires_at.desc())
        .limit(10)
    )
    expired_docs = expired_docs_result.scalars().all()

    # Dossiers with missing documents
    missing_docs_result = await db.execute(
        select(Dossier)
        .where(Dossier.status == DossierStatus.documents_manquants)
        .order_by(Dossier.updated_at.desc())
        .limit(10)
    )
    missing_docs_dossiers = missing_docs_result.scalars().all()

    return {
        "expiring_documents": [
            {
                "document_id": doc.id,
                "dossier_id": doc.dossier_id,
                "document_type": doc.document_type.value
                if hasattr(doc.document_type, "value")
                else doc.document_type,
                "file_name": doc.file_name,
                "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
                "days_remaining": (doc.expires_at.replace(tzinfo=None) - now_naive).days
                if doc.expires_at
                else None,
            }
            for doc in expiring_docs
        ],
        "expired_documents": [
            {
                "document_id": doc.id,
                "dossier_id": doc.dossier_id,
                "document_type": doc.document_type.value
                if hasattr(doc.document_type, "value")
                else doc.document_type,
                "file_name": doc.file_name,
                "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
            }
            for doc in expired_docs
        ],
        "dossiers_missing_documents": [
            {
                "dossier_id": d.id,
                "candidate_id": d.candidate_id,
                "program_id": d.program_id,
                "updated_at": d.updated_at.isoformat(),
            }
            for d in missing_docs_dossiers
        ],
    }


# PLACEHOLDER_RECENT


@router.get("/recent-notifications")
async def get_recent_notifications(
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get latest notifications (WhatsApp/SMS sent)."""
    result = await db.execute(
        select(WhatsAppNotification).order_by(WhatsAppNotification.sent_at.desc()).limit(limit)
    )
    notifications = result.scalars().all()

    return [
        {
            "id": n.id,
            "event_type": n.event_type,
            "to_number": n.to_number,
            "message": n.message[:100],
            "status": n.status.value if hasattr(n.status, "value") else n.status,
            "channel": n.channel,
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
        }
        for n in notifications
    ]


@router.get("/recent-dossiers")
async def get_recent_dossiers(
    limit: int = Query(default=10, le=50),
    program_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    assigned_to: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get recently updated dossiers with optional filters."""
    query = select(Dossier)

    # Apply filters
    if program_id is not None:
        query = query.where(Dossier.program_id == program_id)
    if status is not None:
        query = query.where(Dossier.status == status)
    if assigned_to is not None:
        query = query.where(Dossier.assigned_to == assigned_to)

    query = query.order_by(Dossier.updated_at.desc()).limit(limit)
    result = await db.execute(query)
    dossiers = result.scalars().all()

    return [
        {
            "id": d.id,
            "candidate_id": d.candidate_id,
            "program_id": d.program_id,
            "assigned_to": d.assigned_to,
            "status": d.status.value if hasattr(d.status, "value") else d.status,
            "compliance_score": d.compliance_score,
            "reference_number": d.reference_number,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        }
        for d in dossiers
    ]


@router.get("/stats-by-program")
async def get_stats_by_program(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get dossier statistics grouped by program."""
    result = await db.execute(
        select(
            Program.id,
            Program.name,
            func.count(Dossier.id).label("total"),
            func.avg(Dossier.compliance_score).label("avg_score"),
        )
        .join(Dossier, Dossier.program_id == Program.id, isouter=True)
        .group_by(Program.id, Program.name)
    )
    rows = result.all()

    return [
        {
            "program_id": row[0],
            "program_name": row[1],
            "total_dossiers": row[2],
            "average_score": round(row[3], 1) if row[3] else None,
        }
        for row in rows
    ]
