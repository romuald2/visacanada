"""Family dossier API: link candidates, share documents, coordinated view."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.document import Document
from app.models.dossier import Dossier
from app.models.family import (
    FamilyGroup,
    FamilyMember,
    FamilyRole,
    SharedDocument,
)
from app.models.user import User, UserRole

router = APIRouter(prefix="/family", tags=["family"])

_roles = require_role(UserRole.admin, UserRole.consultant)


class CreateFamilyRequest(BaseModel):
    name: str
    principal_candidate_id: int


class AddMemberRequest(BaseModel):
    candidate_id: int
    role: str = "autre"


class ShareDocumentRequest(BaseModel):
    document_id: int
    note: str | None = None


async def _get_group(group_id: int, db: AsyncSession) -> FamilyGroup:
    result = await db.execute(
        select(FamilyGroup).where(FamilyGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Groupe familial non trouve")
    return group


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_family(
    body: CreateFamilyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Create a family group; the principal candidate is added as first member."""
    cand = await db.execute(
        select(Candidate).where(Candidate.id == body.principal_candidate_id)
    )
    if cand.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Candidat principal non trouve")

    group = FamilyGroup(
        name=body.name,
        principal_candidate_id=body.principal_candidate_id,
        created_by=current_user.id,
    )
    db.add(group)
    await db.flush()

    db.add(
        FamilyMember(
            family_group_id=group.id,
            candidate_id=body.principal_candidate_id,
            role=FamilyRole.principal,
        )
    )
    await db.commit()
    await db.refresh(group)
    return {"id": group.id, "name": group.name}


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    group_id: int,
    body: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Add a candidate to a family group."""
    await _get_group(group_id, db)

    cand = await db.execute(
        select(Candidate).where(Candidate.id == body.candidate_id)
    )
    if cand.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Candidat non trouve")

    try:
        role = FamilyRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Role invalide: {body.role}")

    # Prevent duplicate membership
    existing = await db.execute(
        select(FamilyMember).where(
            FamilyMember.family_group_id == group_id,
            FamilyMember.candidate_id == body.candidate_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409, detail="Candidat deja membre du groupe"
        )

    member = FamilyMember(
        family_group_id=group_id,
        candidate_id=body.candidate_id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return {"id": member.id, "candidate_id": member.candidate_id, "role": member.role.value}


@router.delete("/{group_id}/members/{candidate_id}")
async def remove_member(
    group_id: int,
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Remove a candidate from a family group (cannot remove the principal)."""
    group = await _get_group(group_id, db)
    if candidate_id == group.principal_candidate_id:
        raise HTTPException(
            status_code=400, detail="Impossible de retirer le candidat principal"
        )
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.family_group_id == group_id,
            FamilyMember.candidate_id == candidate_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Membre non trouve")
    await db.delete(member)
    await db.commit()
    return {"detail": "Membre retire"}


@router.post("/{group_id}/shared-documents", status_code=status.HTTP_201_CREATED)
async def share_document(
    group_id: int,
    body: ShareDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Share a document across the family group."""
    await _get_group(group_id, db)

    doc = await db.execute(select(Document).where(Document.id == body.document_id))
    if doc.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Document non trouve")

    existing = await db.execute(
        select(SharedDocument).where(
            SharedDocument.family_group_id == group_id,
            SharedDocument.document_id == body.document_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Document deja partage")

    shared = SharedDocument(
        family_group_id=group_id,
        document_id=body.document_id,
        shared_by=current_user.id,
        note=body.note,
    )
    db.add(shared)
    await db.commit()
    await db.refresh(shared)
    return {"id": shared.id, "document_id": shared.document_id}


@router.get("")
async def list_families(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """List all family groups with member counts."""
    result = await db.execute(select(FamilyGroup).order_by(FamilyGroup.created_at.desc()))
    groups = result.scalars().all()

    output = []
    for g in groups:
        members = await db.execute(
            select(FamilyMember).where(FamilyMember.family_group_id == g.id)
        )
        output.append(
            {
                "id": g.id,
                "name": g.name,
                "principal_candidate_id": g.principal_candidate_id,
                "member_count": len(members.scalars().all()),
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
        )
    return output


@router.get("/{group_id}")
async def family_view(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Coordinated family view: members, their dossiers, and shared documents."""
    group = await _get_group(group_id, db)

    # Members with candidate info and their dossiers
    member_result = await db.execute(
        select(FamilyMember).where(FamilyMember.family_group_id == group_id)
    )
    members = member_result.scalars().all()

    member_views = []
    for m in members:
        cand_result = await db.execute(
            select(Candidate).where(Candidate.id == m.candidate_id)
        )
        candidate = cand_result.scalar_one_or_none()

        doss_result = await db.execute(
            select(Dossier).where(Dossier.candidate_id == m.candidate_id)
        )
        dossiers = doss_result.scalars().all()

        member_views.append(
            {
                "candidate_id": m.candidate_id,
                "role": m.role.value,
                "name": f"{candidate.first_name} {candidate.last_name}"
                if candidate
                else None,
                "dossiers": [
                    {
                        "id": d.id,
                        "status": d.status.value,
                        "reference_number": d.reference_number,
                    }
                    for d in dossiers
                ],
            }
        )

    # Shared documents
    shared_result = await db.execute(
        select(SharedDocument).where(SharedDocument.family_group_id == group_id)
    )
    shared = shared_result.scalars().all()
    shared_docs = []
    for s in shared:
        doc_result = await db.execute(
            select(Document).where(Document.id == s.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        shared_docs.append(
            {
                "shared_id": s.id,
                "document_id": s.document_id,
                "file_name": doc.file_name if doc else None,
                "document_type": doc.document_type.value if doc else None,
                "note": s.note,
            }
        )

    return {
        "id": group.id,
        "name": group.name,
        "principal_candidate_id": group.principal_candidate_id,
        "members": member_views,
        "shared_documents": shared_docs,
    }
