"""Tests for IRCC profile pre-fill system."""

import json
import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Base, User, UserRole
from app.models.candidate import Candidate
from app.models.dossier import Dossier, DossierStatus
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.program import Program, ImmigrationProgram
from app.services.ircc_profile import IRCCProfileService, ircc_profile_service

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


async def setup_dossier_with_docs(
    program_code=ImmigrationProgram.express_entry_fsw,
    extracted_data: dict | None = None,
) -> tuple[int, dict]:
    """Create admin + dossier with candidate and optional extracted docs."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@ircc.com",
            hashed_password=hash_password("pass"),
            full_name="Admin IRCC",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        candidate = Candidate(
            first_name="Marie",
            last_name="Tremblay",
            email="marie@test.com",
            phone="+1-514-555-0123",
            nationality="France",
            current_country="France",
        )
        program = Program(
            code=program_code,
            name="Federal Skilled Worker",
            category="Express Entry",
            is_active=True,
        )
        session.add_all([candidate, program])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.en_cours,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        # Add document with extracted data
        if extracted_data:
            doc = Document(
                dossier_id=dossier.id,
                document_type=DocumentType.passport,
                status=DocumentStatus.verified,
                file_name="passport.pdf",
                file_path_s3="docs/passport.pdf",
                mime_type="application/pdf",
                extracted_data=json.dumps(extracted_data),
            )
            session.add(doc)
            await session.commit()

        token = create_access_token(
            {"sub": str(admin.id), "email": admin.email, "role": "admin"}
        )
        headers = {"Authorization": f"Bearer {token}"}

        return dossier.id, headers


# =============================================================================
# IRCCProfileService Unit Tests
# =============================================================================


class TestIRCCProfileService:
    """Unit tests for the IRCCProfileService."""

    def test_generate_profile_basic(self):
        """Generate profile with candidate data only."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={
                "first_name": "Marie",
                "last_name": "Tremblay",
                "email": "marie@test.com",
                "nationality": "France",
            },
            extracted_documents=[],
        )
        assert profile["program_category"] == "express_entry"
        assert profile["filled_fields"] > 0
        assert profile["total_fields"] > 0
        assert "sections" in profile
        assert "personal_info" in profile["sections"]

    def test_generate_profile_with_extracted(self):
        """Generate profile merging candidate + extracted data."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={"first_name": "Marie", "last_name": "Tremblay"},
            extracted_documents=[
                {
                    "fields": {
                        "passport_number": {"value": "AB123456", "confidence": 0.99},
                        "issue_date": {"value": "2020-01-15", "confidence": 0.95},
                        "expiry_date": {"value": "2030-01-15", "confidence": 0.95},
                        "issuing_country": {"value": "FRA", "confidence": 0.99},
                    }
                }
            ],
        )
        # Passport fields should be filled
        passport_section = profile["sections"]["passport_info"]
        passport_num = next(f for f in passport_section if f["ircc_field"] == "passport_number")
        assert passport_num["value"] == "AB123456"
        assert passport_num["filled"] is True

    def test_missing_required_fields_detected(self):
        """Missing mandatory fields should be reported."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={},  # No data at all
            extracted_documents=[],
        )
        assert len(profile["missing_required"]) > 0
        assert profile["is_ready"] is False
        # family_name should be in missing
        missing_fields = [m["field"] for m in profile["missing_required"]]
        assert "family_name" in missing_fields

    def test_validation_invalid_date(self):
        """Invalid date format should produce validation error."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={"date_of_birth": "not-a-date", "first_name": "Test", "last_name": "User"},
            extracted_documents=[],
        )
        errors = [e for e in profile["validation_errors"] if e["field"] == "date_of_birth"]
        assert len(errors) > 0

    def test_validation_valid_date(self):
        """Valid date should not produce validation error."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={
                "date_of_birth": "1990-05-15",
                "first_name": "Test",
                "last_name": "User",
            },
            extracted_documents=[],
        )
        errors = [e for e in profile["validation_errors"] if e["field"] == "date_of_birth"]
        assert len(errors) == 0

    def test_validation_invalid_email(self):
        """Invalid email should produce validation error."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={"email": "not-an-email", "first_name": "T", "last_name": "U"},
            extracted_documents=[],
        )
        errors = [e for e in profile["validation_errors"] if e["field"] == "email"]
        assert len(errors) > 0

    def test_completeness_calculation(self):
        """Completeness should reflect filled vs total fields."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={},
            extracted_documents=[],
        )
        assert profile["completeness_percent"] == 0.0

    def test_study_permit_mapping(self):
        """Study permit should have study_info section."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="study_permit",
            candidate_data={"first_name": "Test", "last_name": "Student"},
            extracted_documents=[],
        )
        assert "study_info" in profile["sections"]
        assert "financial" in profile["sections"]

    def test_work_permit_mapping(self):
        """Work permit should have employment_info section."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="work_permit",
            candidate_data={"first_name": "Test", "last_name": "Worker"},
            extracted_documents=[],
        )
        assert "employment_info" in profile["sections"]

    def test_export_profile_json(self):
        """Export should produce clean JSON structure."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="express_entry",
            candidate_data={"first_name": "Marie", "last_name": "Tremblay", "email": "m@t.com"},
            extracted_documents=[],
        )
        export = service.export_profile_json(profile)
        assert export["program"] == "express_entry"
        assert "fields" in export
        assert export["fields"]["personal_info"]["family_name"] == "Tremblay"

    def test_get_submission_guide(self):
        """Submission guide should return steps."""
        service = IRCCProfileService()
        guide = service.get_submission_guide("express_entry")
        assert len(guide) > 0
        assert guide[0]["step"] == 1

    def test_unknown_program_falls_back(self):
        """Unknown program should fallback to express_entry."""
        service = IRCCProfileService()
        profile = service.generate_profile(
            program_category="unknown_program",
            candidate_data={"first_name": "X", "last_name": "Y"},
            extracted_documents=[],
        )
        assert "personal_info" in profile["sections"]


# =============================================================================
# IRCC Profile API Tests
# =============================================================================


class TestIRCCProfileAPI:
    """Integration tests for IRCC profile API endpoints."""

    @pytest.mark.anyio
    async def test_generate_profile(self, client):
        """Generate IRCC profile for a dossier."""
        dossier_id, headers = await setup_dossier_with_docs(
            extracted_data={
                "fields": {
                    "passport_number": {"value": "CD789012", "confidence": 0.99},
                    "expiry_date": {"value": "2028-06-01", "confidence": 0.95},
                }
            }
        )

        response = await client.post(
            f"/ircc-profile/dossiers/{dossier_id}/generate",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["program_category"] == "express_entry"
        assert data["filled_fields"] > 0
        assert "sections" in data

    @pytest.mark.anyio
    async def test_generate_profile_not_found(self, client):
        """Generate returns 404 for non-existent dossier."""
        _, headers = await setup_dossier_with_docs()
        response = await client.post(
            "/ircc-profile/dossiers/9999/generate",
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_export_profile(self, client):
        """Export profile as JSON."""
        dossier_id, headers = await setup_dossier_with_docs()

        response = await client.get(
            f"/ircc-profile/dossiers/{dossier_id}/export",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["program"] == "express_entry"
        assert "fields" in data

    @pytest.mark.anyio
    async def test_get_guide(self, client):
        """Get submission guide for dossier program."""
        dossier_id, headers = await setup_dossier_with_docs()

        response = await client.get(
            f"/ircc-profile/dossiers/{dossier_id}/guide",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["program_category"] == "express_entry"
        assert len(data["steps"]) > 0
        assert data["steps"][0]["step"] == 1

    @pytest.mark.anyio
    async def test_candidat_can_view_guide(self, client):
        """Candidat can access submission guide."""
        dossier_id, _ = await setup_dossier_with_docs()

        async with TestSessionLocal() as session:
            candidat = User(
                email="candidat@ircc.com",
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

        response = await client.get(
            f"/ircc-profile/dossiers/{dossier_id}/guide",
            headers=headers,
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_candidat_cannot_generate(self, client):
        """Candidat cannot generate profiles (admin/consultant only)."""
        dossier_id, _ = await setup_dossier_with_docs()

        async with TestSessionLocal() as session:
            candidat = User(
                email="candidat2@ircc.com",
                hashed_password=hash_password("pass"),
                full_name="Candidat2",
                role=UserRole.candidat,
            )
            session.add(candidat)
            await session.commit()
            await session.refresh(candidat)

            token = create_access_token(
                {"sub": str(candidat.id), "email": candidat.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            f"/ircc-profile/dossiers/{dossier_id}/generate",
            headers=headers,
        )
        assert response.status_code == 403
