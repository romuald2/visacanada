"""Candidate data export endpoint (PIPEDA Principle 9)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.dossier import Dossier
from app.models.document import Document
from app.models.user import User

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/export")
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all personal data for the current user (PIPEDA Principle 9)."""
    # User data
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value if hasattr(current_user.role, "value") else current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat(),
    }

    # Candidate profile (if exists)
    candidate_data = None
    res = await db.execute(select(Candidate).where(Candidate.user_id == current_user.id))
    candidate = res.scalar_one_or_none()
    if candidate:
        candidate_data = {
            "id": candidate.id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "date_of_birth": candidate.date_of_birth.isoformat() if candidate.date_of_birth else None,
            "nationality": candidate.nationality,
            "passport_number": candidate.passport_number,
            "passport_expiry": candidate.passport_expiry.isoformat() if candidate.passport_expiry else None,
            "address": candidate.address,
            "consent_given": candidate.consent_given,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
        }

        # Dossiers
        dossiers_res = await db.execute(
            select(Dossier).where(Dossier.candidate_id == candidate.id)
        )
        dossiers = dossiers_res.scalars().all()
        dossiers_data = []
        for d in dossiers:
            # Documents for this dossier
            docs_res = await db.execute(
                select(Document).where(Document.dossier_id == d.id)
            )
            documents = docs_res.scalars().all()
            docs_data = [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "requirement_id": doc.requirement_id,
                    "s3_key": doc.s3_key,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
                    "status": doc.status,
                    # Note: actual file content not included for size reasons
                }
                for doc in documents
            ]

            dossiers_data.append({
                "id": d.id,
                "program_id": d.program_id,
                "status": d.status,
                "reference_number": d.reference_number,
                "notes": d.notes,
                "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
                "decision_at": d.decision_at.isoformat() if d.decision_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                "documents": docs_data,
            })

        candidate_data["dossiers"] = dossiers_data

    export_data = {
        "export_date": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "user": user_data,
        "candidate": candidate_data,
        "notice": (
            "Cet export contient toutes vos donnees personnelles conservees par VisaCanada. "
            "Conformement a la PIPEDA (Principe 9), vous avez le droit d'acceder a vos donnees "
            "et de demander leur correction si necessaire. Pour toute question, contactez "
            "privacy@visacanada.com."
        ),
    }

    import json
    json_content = json.dumps(export_data, indent=2, ensure_ascii=False)

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=visacanada_export_{current_user.id}.json"
        },
    )
