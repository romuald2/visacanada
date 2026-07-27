"""Tests for CRS Calculator."""

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Base, User, UserRole
from app.models.candidate import Candidate
from app.services.crs_calculator import (
    CRSCalculator,
    CRSInput,
    LanguageScore,
    ielts_to_clb,
    language_to_clb,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
# PLACEHOLDER_HELPERS


async def create_admin() -> dict:
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@crs.com",
            hashed_password=hash_password("pass"),
            full_name="Admin CRS",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(
            {"sub": str(admin.id), "email": admin.email, "role": "admin"}
        )
        return {"headers": {"Authorization": f"Bearer {token}"}, "user_id": admin.id}


async def create_candidate(user_id: int) -> int:
    async with TestSessionLocal() as session:
        candidate = Candidate(
            user_id=user_id,
            first_name="Jean",
            last_name="Dupont",
            email="jean@crs.com",
            nationality="FR",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)
        return candidate.id


# =============================================================================
# Unit Tests - CLB Conversion
# =============================================================================


class TestCLBConversion:
    """Tests for IELTS to CLB conversion."""

    def test_ielts_reading_high(self):
        assert ielts_to_clb(8.0, "reading") == 10

    def test_ielts_reading_mid(self):
        assert ielts_to_clb(6.5, "reading") == 8

    def test_ielts_reading_low(self):
        assert ielts_to_clb(3.5, "reading") == 4

    def test_ielts_below_min(self):
        assert ielts_to_clb(2.0, "reading") == 3

    def test_language_to_clb_ielts(self):
        lang = LanguageScore(reading=7.0, writing=7.0, listening=8.0, speaking=7.0, test_type="ielts")
        clb = language_to_clb(lang)
        assert clb["reading"] == 9
        assert clb["writing"] == 9
        assert clb["listening"] == 9
        assert clb["speaking"] == 9

    def test_language_to_clb_tef(self):
        """TEF/TCF uses direct CLB values."""
        lang = LanguageScore(reading=9, writing=8, listening=9, speaking=8, test_type="tef")
        clb = language_to_clb(lang)
        assert clb["reading"] == 9
        assert clb["writing"] == 8


# =============================================================================
# Unit Tests - CRS Calculator
# =============================================================================


class TestCRSCalculator:
    """Unit tests for CRS scoring logic."""

    def test_young_single_high_score(self):
        """Young single with strong profile."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=28,
            marital_status="single",
            education_level="masters",
            first_language=LanguageScore(reading=8.0, writing=7.5, listening=8.5, speaking=7.5, test_type="ielts"),
            canadian_experience_years=3,
            foreign_experience_years=3,
        ))
        assert result["total_score"] > 450
        assert result["breakdown"]["core_human_capital"]["age"] == 110
        assert result["breakdown"]["core_human_capital"]["education"] == 135

    def test_age_45_zero_points(self):
        """Age 45+ gets zero age points."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=45,
            first_language=LanguageScore(reading=6.0, writing=6.0, listening=6.0, speaking=6.0, test_type="ielts"),
        ))
        assert result["breakdown"]["core_human_capital"]["age"] == 0

    def test_married_lower_core_points(self):
        """Married applicants get lower individual points."""
        calc = CRSCalculator()
        single = calc.calculate(CRSInput(
            age=30,
            marital_status="single",
            education_level="bachelors",
            first_language=LanguageScore(reading=7.0, writing=7.0, listening=7.0, speaking=7.0, test_type="ielts"),
        ))
        married = calc.calculate(CRSInput(
            age=30,
            marital_status="married",
            education_level="bachelors",
            first_language=LanguageScore(reading=7.0, writing=7.0, listening=7.0, speaking=7.0, test_type="ielts"),
        ))
        # Single gets more core points
        assert single["breakdown"]["core_human_capital"]["subtotal"] > married["breakdown"]["core_human_capital"]["subtotal"]

    def test_pnp_adds_600(self):
        """Provincial nomination adds 600 points."""
        calc = CRSCalculator()
        without = calc.calculate(CRSInput(
            age=30,
            first_language=LanguageScore(reading=6.0, writing=6.0, listening=6.0, speaking=6.0, test_type="ielts"),
        ))
        with_pnp = calc.calculate(CRSInput(
            age=30,
            first_language=LanguageScore(reading=6.0, writing=6.0, listening=6.0, speaking=6.0, test_type="ielts"),
            has_provincial_nomination=True,
        ))
        assert with_pnp["total_score"] - without["total_score"] == 600

    def test_french_bonus(self):
        """French language adds bonus points."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=30,
            first_language=LanguageScore(reading=7.0, writing=7.0, listening=7.0, speaking=7.0, test_type="ielts"),
            french_language_proficiency="clb7_plus",
        ))
        assert result["breakdown"]["additional_points"]["french_proficiency"] == 50

    def test_skill_transferability_capped_100(self):
        """Skill transferability is capped at 100."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=30,
            education_level="doctoral",
            first_language=LanguageScore(reading=8.0, writing=8.0, listening=8.5, speaking=8.0, test_type="ielts"),
            canadian_experience_years=5,
            foreign_experience_years=5,
        ))
        assert result["breakdown"]["skill_transferability"]["total"] <= 100

    def test_spouse_factors(self):
        """Spouse factors add points."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=30,
            marital_status="married",
            education_level="bachelors",
            first_language=LanguageScore(reading=7.0, writing=7.0, listening=7.0, speaking=7.0, test_type="ielts"),
            spouse_education="masters",
            spouse_language=LanguageScore(reading=7.0, writing=7.0, listening=7.0, speaking=7.0, test_type="ielts"),
            spouse_canadian_experience_years=2,
        ))
        assert result["breakdown"]["spouse_factors"]["subtotal"] > 0
        assert result["breakdown"]["spouse_factors"]["education"] == 10

    def test_recommendations_generated(self):
        """Recommendations are generated."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=35,
            first_language=LanguageScore(reading=6.0, writing=6.0, listening=6.0, speaking=6.0, test_type="ielts"),
        ))
        assert len(result["recommendations"]) > 0

    def test_eligible_for_ita(self):
        """High score candidate marked eligible."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=28,
            education_level="masters",
            first_language=LanguageScore(reading=8.0, writing=7.5, listening=8.5, speaking=7.5, test_type="ielts"),
            canadian_experience_years=3,
            has_provincial_nomination=True,
        ))
        assert result["eligible_for_ita"] is True

    def test_no_education_zero_points(self):
        """No education gives 0 education points."""
        calc = CRSCalculator()
        result = calc.calculate(CRSInput(
            age=30,
            education_level="none",
            first_language=LanguageScore(reading=6.0, writing=6.0, listening=6.0, speaking=6.0, test_type="ielts"),
        ))
        assert result["breakdown"]["core_human_capital"]["education"] == 0
# PLACEHOLDER_API_TESTS


# =============================================================================
# API Integration Tests
# =============================================================================


class TestCRSAPI:
    """Integration tests for CRS API endpoints."""

    @pytest.mark.anyio
    async def test_calculate_basic(self, client):
        """POST /crs/calculate returns score."""
        admin = await create_admin()
        response = await client.post(
            "/crs/calculate",
            headers=admin["headers"],
            json={
                "age": 30,
                "marital_status": "single",
                "education_level": "bachelors",
                "first_language": {
                    "reading": 7.0,
                    "writing": 7.0,
                    "listening": 7.0,
                    "speaking": 7.0,
                    "test_type": "ielts",
                },
                "canadian_experience_years": 1,
                "foreign_experience_years": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_score" in data
        assert "breakdown" in data
        assert "recommendations" in data
        assert data["total_score"] > 0

    @pytest.mark.anyio
    async def test_calculate_with_spouse(self, client):
        """Calculate with spouse factors."""
        admin = await create_admin()
        response = await client.post(
            "/crs/calculate",
            headers=admin["headers"],
            json={
                "age": 32,
                "marital_status": "married",
                "education_level": "masters",
                "first_language": {
                    "reading": 8.0,
                    "writing": 7.5,
                    "listening": 8.5,
                    "speaking": 7.5,
                    "test_type": "ielts",
                },
                "spouse_education": "bachelors",
                "spouse_language": {
                    "reading": 6.5,
                    "writing": 6.5,
                    "listening": 6.5,
                    "speaking": 6.5,
                    "test_type": "ielts",
                },
                "spouse_canadian_experience_years": 1,
                "canadian_experience_years": 2,
                "foreign_experience_years": 4,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["breakdown"]["spouse_factors"]["subtotal"] > 0

    @pytest.mark.anyio
    async def test_simulate_and_save(self, client):
        """POST /crs/simulate/{id} saves simulation."""
        admin = await create_admin()
        candidate_id = await create_candidate(admin["user_id"])

        response = await client.post(
            f"/crs/simulate/{candidate_id}",
            headers=admin["headers"],
            json={
                "age": 28,
                "marital_status": "single",
                "education_level": "bachelors",
                "first_language": {
                    "reading": 7.0,
                    "writing": 7.0,
                    "listening": 7.0,
                    "speaking": 7.0,
                    "test_type": "ielts",
                },
                "canadian_experience_years": 0,
                "foreign_experience_years": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data
        assert data["total_score"] > 0

    @pytest.mark.anyio
    async def test_simulate_candidate_not_found(self, client):
        """Simulate for non-existent candidate returns 404."""
        admin = await create_admin()
        response = await client.post(
            "/crs/simulate/999",
            headers=admin["headers"],
            json={
                "age": 30,
                "marital_status": "single",
                "education_level": "bachelors",
                "first_language": {
                    "reading": 6.0, "writing": 6.0,
                    "listening": 6.0, "speaking": 6.0,
                    "test_type": "ielts",
                },
            },
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_history(self, client):
        """GET /crs/history/{id} returns saved simulations."""
        admin = await create_admin()
        candidate_id = await create_candidate(admin["user_id"])

        # Save one simulation first
        await client.post(
            f"/crs/simulate/{candidate_id}",
            headers=admin["headers"],
            json={
                "age": 30,
                "marital_status": "single",
                "education_level": "bachelors",
                "first_language": {
                    "reading": 7.0, "writing": 7.0,
                    "listening": 7.0, "speaking": 7.0,
                    "test_type": "ielts",
                },
            },
        )

        response = await client.get(
            f"/crs/history/{candidate_id}", headers=admin["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["total_score"] > 0

    @pytest.mark.anyio
    async def test_rounds(self, client):
        """GET /crs/rounds returns recent invitation rounds."""
        admin = await create_admin()
        response = await client.get("/crs/rounds", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "date" in data[0]
        assert "score" in data[0]

    @pytest.mark.anyio
    async def test_candidat_forbidden(self, client):
        """Candidat cannot access CRS endpoints."""
        async with TestSessionLocal() as session:
            candidat = User(
                email="candidat@crs.com",
                hashed_password=hash_password("pass"),
                full_name="Candidat",
                role=UserRole.candidat,
            )
            session.add(candidat)
            await session.commit()
            await session.refresh(candidat)
            token = create_access_token(
                {"sub": str(candidat.id), "email": candidat.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/crs/rounds", headers=headers)
        assert response.status_code == 403
