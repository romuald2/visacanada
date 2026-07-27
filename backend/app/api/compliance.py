"""Compliance verification API router."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.document import Document
from app.models.dossier import Dossier
from app.models.program import Program
from app.models.program_requirement import ProgramRequirement
from app.models.user import User, UserRole
from app.schemas.compliance import (
    ComplianceScoreResponse,
    ComplianceStatusResponse,
    ComplianceVerifyRequest,
)
from app.services.compliance_agent import compliance_agent
from app.services.scoring_engine import scoring_engine

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post(
    "/dossiers/{dossier_id}/verify",
    response_model=ComplianceScoreResponse,
)
async def verify_dossier_compliance(
    dossier_id: int,
    body: ComplianceVerifyRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Run compliance verification on a dossier.

    Analyzes all documents against program requirements.
    Uses AI (Claude) when available, falls back to rule-based.
    """
    force_refresh = body.force_refresh if body else False

    # Get dossier
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Check if cached result is available and not forced refresh
    if not force_refresh and dossier.compliance_details and dossier.last_verified_at:
        return dossier.compliance_details

    # Get program info
    result = await db.execute(
        select(Program).where(Program.id == dossier.program_id)
    )
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programme non trouvé",
        )

    # Get program requirements
    result = await db.execute(
        select(ProgramRequirement).where(
            ProgramRequirement.program_id == program.id,
            ProgramRequirement.is_active == True,
        )
    )
    requirements = result.scalars().all()

    requirements_data = [
        {
            "document_type": req.document_type,
            "document_name": req.document_name,
            "priority": req.priority.value,
            "description": req.description,
        }
        for req in requirements
    ]

    # Get dossier documents
    result = await db.execute(
        select(Document).where(Document.dossier_id == dossier_id)
    )
    documents = result.scalars().all()

    documents_data = [
        {
            "id": doc.id,
            "file_name": doc.file_name,
            "document_type": doc.document_type.value if hasattr(doc.document_type, "value") else doc.document_type,
            "status": doc.status.value if hasattr(doc.status, "value") else doc.status,
        }
        for doc in documents
    ]

    # Get extracted data from documents
    extracted_data = []
    for doc in documents:
        if doc.extracted_data:
            try:
                fields = json.loads(doc.extracted_data) if isinstance(doc.extracted_data, str) else doc.extracted_data
            except (json.JSONDecodeError, TypeError):
                fields = {}
            extracted_data.append({
                "type": doc.document_type.value if hasattr(doc.document_type, "value") else doc.document_type,
                "fields": fields,
            })

    # Run compliance verification
    compliance_report = await compliance_agent.verify_compliance(
        program_name=program.name,
        program_requirements=requirements_data,
        submitted_documents=documents_data,
        extracted_data=extracted_data,
    )

    # Build score summary
    score_summary = scoring_engine.build_score_summary(compliance_report)

    # Save to dossier
    await scoring_engine.save_score(db, dossier_id, score_summary)

    return score_summary


@router.get(
    "/dossiers/{dossier_id}/score",
    response_model=ComplianceScoreResponse | None,
)
async def get_dossier_score(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest compliance score for a dossier (cached)."""
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Access control for candidats
    if current_user.role == UserRole.candidat:
        from app.models.candidate import Candidate

        result = await db.execute(
            select(Candidate).where(
                Candidate.id == dossier.candidate_id,
                Candidate.user_id == current_user.id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé",
            )

    if not dossier.compliance_details:
        return None

    return dossier.compliance_details


@router.get(
    "/dossiers/{dossier_id}/status",
    response_model=ComplianceStatusResponse,
)
async def get_compliance_status(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a quick compliance status overview for a dossier."""
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Access control for candidats
    if current_user.role == UserRole.candidat:
        from app.models.candidate import Candidate

        result = await db.execute(
            select(Candidate).where(
                Candidate.id == dossier.candidate_id,
                Candidate.user_id == current_user.id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé",
            )

    # Get program name
    result = await db.execute(
        select(Program).where(Program.id == dossier.program_id)
    )
    program = result.scalar_one()

    # Get documents count
    result = await db.execute(
        select(Document).where(Document.dossier_id == dossier_id)
    )
    documents = result.scalars().all()

    # Get mandatory requirements
    result = await db.execute(
        select(ProgramRequirement).where(
            ProgramRequirement.program_id == program.id,
            ProgramRequirement.is_active == True,
            ProgramRequirement.priority == "mandatory",
        )
    )
    mandatory_reqs = result.scalars().all()

    # Determine missing documents
    doc_types = {d.document_type for d in documents}
    missing = [
        req.document_name
        for req in mandatory_reqs
        if req.document_type not in doc_types
    ]

    # Determine status
    score = dossier.compliance_score
    if score is None:
        status_label = "non_verifie"
    else:
        status_label = scoring_engine.get_score_status(score)

    return ComplianceStatusResponse(
        dossier_id=dossier_id,
        program_name=program.name,
        current_score=dossier.compliance_score,
        last_verified_at=dossier.last_verified_at,
        status=status_label,
        documents_count=len(documents),
        missing_mandatory=missing,
    )
