"""CRS Calculator API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.crs_simulation import CRSSimulation
from app.models.user import User, UserRole
from app.services.crs_calculator import (
    CRSInput,
    LanguageScore,
    crs_calculator,
)

router = APIRouter(prefix="/crs", tags=["crs"])


# --- Request/Response schemas ---

class LanguageScoreRequest(BaseModel):
    reading: float = Field(ge=0, le=10)
    writing: float = Field(ge=0, le=10)
    listening: float = Field(ge=0, le=10)
    speaking: float = Field(ge=0, le=10)
    test_type: str = "ielts"


class CRSCalculateRequest(BaseModel):
    age: int = Field(ge=18, le=65)
    marital_status: str = "single"
    education_level: str = "bachelors"
    canadian_education: str = "none"
    first_language: LanguageScoreRequest
    second_language: LanguageScoreRequest | None = None
    canadian_experience_years: int = Field(ge=0, le=10, default=0)
    foreign_experience_years: int = Field(ge=0, le=10, default=0)
    spouse_education: str = "none"
    spouse_language: LanguageScoreRequest | None = None
    spouse_canadian_experience_years: int = Field(ge=0, le=5, default=0)
    has_provincial_nomination: bool = False
    has_arranged_employment: bool = False
    arranged_employment_noc: str = "other"
    has_canadian_sibling: bool = False
    french_language_proficiency: str = "none"
# PLACEHOLDER_API_ENDPOINTS


def _request_to_input(body: CRSCalculateRequest) -> CRSInput:
    """Convert API request to CRSInput dataclass."""
    first_lang = LanguageScore(
        reading=body.first_language.reading,
        writing=body.first_language.writing,
        listening=body.first_language.listening,
        speaking=body.first_language.speaking,
        test_type=body.first_language.test_type,
    )
    second_lang = None
    if body.second_language:
        second_lang = LanguageScore(
            reading=body.second_language.reading,
            writing=body.second_language.writing,
            listening=body.second_language.listening,
            speaking=body.second_language.speaking,
            test_type=body.second_language.test_type,
        )
    spouse_lang = None
    if body.spouse_language:
        spouse_lang = LanguageScore(
            reading=body.spouse_language.reading,
            writing=body.spouse_language.writing,
            listening=body.spouse_language.listening,
            speaking=body.spouse_language.speaking,
            test_type=body.spouse_language.test_type,
        )

    return CRSInput(
        age=body.age,
        marital_status=body.marital_status,
        education_level=body.education_level,
        canadian_education=body.canadian_education,
        first_language=first_lang,
        second_language=second_lang,
        canadian_experience_years=body.canadian_experience_years,
        foreign_experience_years=body.foreign_experience_years,
        spouse_education=body.spouse_education,
        spouse_language=spouse_lang,
        spouse_canadian_experience_years=body.spouse_canadian_experience_years,
        has_provincial_nomination=body.has_provincial_nomination,
        has_arranged_employment=body.has_arranged_employment,
        arranged_employment_noc=body.arranged_employment_noc,
        has_canadian_sibling=body.has_canadian_sibling,
        french_language_proficiency=body.french_language_proficiency,
    )


@router.post("/calculate")
async def calculate_crs(
    body: CRSCalculateRequest,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Calculate CRS score from provided criteria."""
    crs_input = _request_to_input(body)
    result = crs_calculator.calculate(crs_input)
    return result


@router.post("/simulate/{candidate_id}")
async def simulate_and_save(
    candidate_id: int,
    body: CRSCalculateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Calculate CRS and save simulation for a candidate."""
    # Verify candidate exists
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat non trouve")

    crs_input = _request_to_input(body)
    calc_result = crs_calculator.calculate(crs_input)

    # Save simulation
    simulation = CRSSimulation(
        candidate_id=candidate_id,
        calculated_by=current_user.id,
        total_score=calc_result["total_score"],
        input_data=body.model_dump(),
        breakdown=calc_result["breakdown"],
        recommendations=calc_result["recommendations"],
    )
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)

    return {
        "simulation_id": simulation.id,
        **calc_result,
    }


@router.get("/history/{candidate_id}")
async def get_simulation_history(
    candidate_id: int,
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get CRS simulation history for a candidate."""
    result = await db.execute(
        select(CRSSimulation)
        .where(CRSSimulation.candidate_id == candidate_id)
        .order_by(CRSSimulation.created_at.desc())
        .limit(limit)
    )
    simulations = result.scalars().all()

    return [
        {
            "id": s.id,
            "total_score": s.total_score,
            "breakdown": s.breakdown,
            "recommendations": s.recommendations,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in simulations
    ]


@router.get("/rounds")
async def get_recent_rounds(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get recent Express Entry invitation rounds for comparison."""
    return crs_calculator.RECENT_ROUNDS
