"""IRCC Profile pre-fill API router."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.document import Document
from app.models.dossier import Dossier
from app.models.program import Program
from app.models.user import User, UserRole
from app.schemas.ircc_profile import (
    IRCCProfileExportResponse,
    IRCCProfileResponse,
    SubmissionGuideResponse,
)
from app.services.ircc_profile import ircc_profile_service

router = APIRouter(prefix="/ircc-profile", tags=["ircc-profile"])


def _get_program_category(program_code: str) -> str:
    """Map program code to category for field mappings."""
    code = program_code.lower()
    if "express_entry" in code:
        return "express_entry"
    elif "study" in code:
        return "study_permit"
    elif "work_permit" in code:
        return "work_permit"
    return "express_entry"


@router.post(
    "/dossiers/{dossier_id}/generate",
    response_model=IRCCProfileResponse,
)
async def generate_ircc_profile(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Generate a pre-filled IRCC profile from dossier documents.

    Maps OCR-extracted data to IRCC form fields for the relevant program.
    """
    # Get dossier
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouve",
        )

    # Get program
    result = await db.execute(
        select(Program).where(Program.id == dossier.program_id)
    )
    program = result.scalar_one()

    # Get candidate
    result = await db.execute(
        select(Candidate).where(Candidate.id == dossier.candidate_id)
    )
    candidate = result.scalar_one()

    # Build candidate data dict
    candidate_data = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "date_of_birth": str(candidate.date_of_birth) if candidate.date_of_birth else None,
        "nationality": candidate.nationality,
        "current_country": candidate.current_country,
    }

    # Get extracted data from documents
    result = await db.execute(
        select(Document).where(Document.dossier_id == dossier_id)
    )
    documents = result.scalars().all()

    extracted_documents = []
    for doc in documents:
        if doc.extracted_data:
            try:
                data = (
                    json.loads(doc.extracted_data)
                    if isinstance(doc.extracted_data, str)
                    else doc.extracted_data
                )
                extracted_documents.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

    # Determine program category
    program_category = _get_program_category(program.code.value if hasattr(program.code, "value") else program.code)

    # Generate profile
    profile = ircc_profile_service.generate_profile(
        program_category=program_category,
        candidate_data=candidate_data,
        extracted_documents=extracted_documents,
    )

    return profile


@router.get(
    "/dossiers/{dossier_id}/export",
    response_model=IRCCProfileExportResponse,
)
async def export_ircc_profile(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Export pre-filled profile as clean JSON for external use."""
    # Get dossier
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouve",
        )

    # Get program
    result = await db.execute(
        select(Program).where(Program.id == dossier.program_id)
    )
    program = result.scalar_one()

    # Get candidate
    result = await db.execute(
        select(Candidate).where(Candidate.id == dossier.candidate_id)
    )
    candidate = result.scalar_one()

    candidate_data = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "date_of_birth": str(candidate.date_of_birth) if candidate.date_of_birth else None,
        "nationality": candidate.nationality,
        "current_country": candidate.current_country,
    }

    # Get extracted docs
    result = await db.execute(
        select(Document).where(Document.dossier_id == dossier_id)
    )
    documents = result.scalars().all()

    extracted_documents = []
    for doc in documents:
        if doc.extracted_data:
            try:
                data = (
                    json.loads(doc.extracted_data)
                    if isinstance(doc.extracted_data, str)
                    else doc.extracted_data
                )
                extracted_documents.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

    program_category = _get_program_category(program.code.value if hasattr(program.code, "value") else program.code)

    profile = ircc_profile_service.generate_profile(
        program_category=program_category,
        candidate_data=candidate_data,
        extracted_documents=extracted_documents,
    )

    return ircc_profile_service.export_profile_json(profile)


@router.get(
    "/dossiers/{dossier_id}/guide",
    response_model=SubmissionGuideResponse,
)
async def get_submission_guide(
    dossier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get step-by-step IRCC submission guide for the dossier's program."""
    # Get dossier
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouve",
        )

    # Get program
    result = await db.execute(
        select(Program).where(Program.id == dossier.program_id)
    )
    program = result.scalar_one()

    program_category = _get_program_category(program.code.value if hasattr(program.code, "value") else program.code)
    steps = ircc_profile_service.get_submission_guide(program_category)

    return SubmissionGuideResponse(
        program_category=program_category,
        steps=steps,
    )
