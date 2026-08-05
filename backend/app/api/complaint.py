"""Candidate portal complaint endpoint (PIPEDA Principle 10)."""


from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.user import User, UserRole
from app.services.smtp_sender import smtp_sender

router = APIRouter(prefix="/portal", tags=["portal"])


class ComplaintCreate(BaseModel):
    subject: str
    description: str


@router.post("/complaint", status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    body: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a complaint regarding personal data (PIPEDA Principle 10)."""
    if not body.subject.strip() or not body.description.strip():
        raise HTTPException(status_code=400, detail="Sujet et description requis")

    complaint = Complaint(
        user_id=current_user.id,
        subject=body.subject.strip(),
        description=body.description.strip(),
        status="nouveau",
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)

    # Notify admin by email (best effort)
    try:
        admin_res = await db.execute(
            select(User).where(User.role == UserRole.admin).where(User.is_active)
        )
        admins = admin_res.scalars().all()

        for admin in admins:
            if admin.email:
                smtp_sender.send_email(
                    to=admin.email,
                    subject=f"Nouvelle plainte PIPEDA - {body.subject}",
                    body=(
                        f"Une nouvelle plainte a ete soumise par {current_user.full_name} "
                        f"({current_user.email}).\n\n"
                        f"Sujet: {body.subject}\n"
                        f"Description:\n{body.description}\n\n"
                        f"ID plainte: {complaint.id}\n"
                        f"Veuillez traiter cette plainte dans les meilleurs delais."
                    ),
                )
    except Exception:
        pass  # Email failure should not block complaint submission

    return {
        "id": complaint.id,
        "subject": complaint.subject,
        "status": complaint.status,
        "created_at": complaint.created_at.isoformat() if complaint.created_at else None,
        "detail": "Plainte soumise avec succes. Un administrateur la traitera sous peu.",
    }


@router.get("/complaints")
async def list_my_complaints(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's complaints."""
    res = await db.execute(
        select(Complaint)
        .where(Complaint.user_id == current_user.id)
        .order_by(Complaint.created_at.desc())
    )
    complaints = res.scalars().all()
    return [
        {
            "id": c.id,
            "subject": c.subject,
            "description": c.description,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            "admin_response": c.admin_response,
        }
        for c in complaints
    ]
