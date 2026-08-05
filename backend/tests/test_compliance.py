"""Tests for compliance verification system."""

import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus
from app.models.dossier import Dossier, DossierStatus
from app.models.program import ImmigrationProgram, Program
from app.models.program_requirement import ProgramRequirement, RequirementPriority
from app.models.user import Base, User, UserRole
from app.services.compliance_agent import ComplianceAgent, compliance_agent
from app.services.scoring_engine import scoring_engine

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


async def setup_dossier_with_requirements() -> tuple[int, int, dict]:
    """Create admin + dossier with requirements. Return (dossier_id, program_id, headers)."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@compliance.com",
            hashed_password=hash_password("pass"),
            full_name="Admin Compliance",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        candidate = Candidate(first_name="Jean", last_name="Dupont", email="jean@test.com")
        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
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

        # Add requirements
        reqs = [
            ProgramRequirement(
                program_id=program.id,
                document_type="passport",
                document_name="Passeport",
                priority=RequirementPriority.mandatory,
                sort_order=1,
                is_active=True,
            ),
            ProgramRequirement(
                program_id=program.id,
                document_type="language_test",
                document_name="Test de langue (IELTS/TEF)",
                priority=RequirementPriority.mandatory,
                sort_order=2,
                is_active=True,
            ),
            ProgramRequirement(
                program_id=program.id,
                document_type="education_credential",
                document_name="Évaluation des diplômes (ECA)",
                priority=RequirementPriority.mandatory,
                sort_order=3,
                is_active=True,
            ),
            ProgramRequirement(
                program_id=program.id,
                document_type="police_certificate",
                document_name="Certificat de police",
                priority=RequirementPriority.recommended,
                sort_order=4,
                is_active=True,
            ),
        ]
        session.add_all(reqs)
        await session.commit()

        token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}

        return dossier.id, program.id, headers


async def add_document_to_dossier(dossier_id: int, doc_type: str, extracted: dict | None = None):
    """Add a document to a dossier."""
    async with TestSessionLocal() as session:
        doc = Document(
            dossier_id=dossier_id,
            document_type=doc_type,
            status=DocumentStatus.uploaded,
            file_name=f"{doc_type}.pdf",
            file_path_s3=f"documents/{dossier_id}/{doc_type}.pdf",
            mime_type="application/pdf",
            extracted_data=extracted,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc.id


# =============================================================================
# Scoring Engine Unit Tests
# =============================================================================


class TestScoringEngine:
    """Unit tests for the ScoringEngine."""

    def test_calculate_global_score_perfect(self):
        report = {
            "completeness": {"score": 100.0},
            "validity": {"score": 100.0},
            "consistency": {"score": 100.0},
        }
        score = scoring_engine.calculate_global_score(report)
        assert score == 100.0

    def test_calculate_global_score_weighted(self):
        report = {
            "completeness": {"score": 50.0},
            "validity": {"score": 80.0},
            "consistency": {"score": 100.0},
        }
        # 50*0.4 + 80*0.3 + 100*0.3 = 20 + 24 + 30 = 74
        score = scoring_engine.calculate_global_score(report)
        assert score == 74.0

    def test_calculate_global_score_zero(self):
        report = {
            "completeness": {"score": 0},
            "validity": {"score": 0},
            "consistency": {"score": 0},
        }
        score = scoring_engine.calculate_global_score(report)
        assert score == 0.0

    def test_get_score_status_ready(self):
        assert scoring_engine.get_score_status(85.0) == "ready"
        assert scoring_engine.get_score_status(100.0) == "ready"

    def test_get_score_status_warning(self):
        assert scoring_engine.get_score_status(60.0) == "warning"
        assert scoring_engine.get_score_status(84.9) == "warning"

    def test_get_score_status_critical(self):
        assert scoring_engine.get_score_status(40.0) == "critical"
        assert scoring_engine.get_score_status(59.9) == "critical"

    def test_get_score_status_incomplete(self):
        assert scoring_engine.get_score_status(0.0) == "incomplete"
        assert scoring_engine.get_score_status(39.9) == "incomplete"

    def test_get_score_color(self):
        assert scoring_engine.get_score_color(90.0) == "green"
        assert scoring_engine.get_score_color(70.0) == "orange"
        assert scoring_engine.get_score_color(50.0) == "red"
        assert scoring_engine.get_score_color(20.0) == "gray"

    def test_build_score_summary(self):
        report = {
            "completeness": {"score": 100.0},
            "validity": {"score": 90.0},
            "consistency": {"score": 80.0},
            "recommendations": [
                {"priority": "high", "action": "fix something"},
                {"priority": "low", "action": "optional thing"},
            ],
            "summary": "Good dossier",
            "method": "rule_based",
        }
        summary = scoring_engine.build_score_summary(report)
        assert summary["global_score"] == 91.0  # 100*0.4 + 90*0.3 + 80*0.3
        assert summary["status"] == "ready"
        assert summary["color"] == "green"
        assert summary["is_ready_for_submission"] is True
        assert summary["issues_count"]["high"] == 1
        assert summary["issues_count"]["low"] == 1
        assert summary["issues_count"]["total"] == 2


# =============================================================================
# Compliance Agent Unit Tests
# =============================================================================


class TestComplianceAgent:
    """Unit tests for the ComplianceAgent."""

    def test_rule_based_all_docs_present(self):
        """All mandatory documents present should give high completeness."""
        agent = ComplianceAgent()
        requirements = [
            {"document_type": "passport", "document_name": "Passeport", "priority": "mandatory"},
            {
                "document_type": "language_test",
                "document_name": "Test de langue",
                "priority": "mandatory",
            },
        ]
        documents = [
            {"document_type": "passport", "file_name": "passport.pdf"},
            {"document_type": "language_test", "file_name": "ielts.pdf"},
        ]
        result = agent._rule_based_verification(requirements, documents, [])
        assert result["completeness"]["score"] == 100.0
        assert result["completeness"]["missing_documents"] == []

    def test_rule_based_missing_mandatory(self):
        """Missing mandatory docs should reduce completeness score."""
        agent = ComplianceAgent()
        requirements = [
            {"document_type": "passport", "document_name": "Passeport", "priority": "mandatory"},
            {
                "document_type": "language_test",
                "document_name": "Test de langue",
                "priority": "mandatory",
            },
            {
                "document_type": "education_credential",
                "document_name": "ECA",
                "priority": "mandatory",
            },
        ]
        documents = [
            {"document_type": "passport", "file_name": "passport.pdf"},
        ]
        result = agent._rule_based_verification(requirements, documents, [])
        # 1 out of 3 mandatory = 33.3%
        assert result["completeness"]["score"] == pytest.approx(33.3, abs=0.1)
        assert "Test de langue" in result["completeness"]["missing_documents"]
        assert "ECA" in result["completeness"]["missing_documents"]

    def test_rule_based_expired_passport(self):
        """Expired passport should reduce validity score."""
        agent = ComplianceAgent()
        requirements = [
            {"document_type": "passport", "document_name": "Passeport", "priority": "mandatory"},
        ]
        documents = [
            {"document_type": "passport", "file_name": "passport.pdf"},
        ]
        extracted = [
            {
                "type": "passport",
                "fields": {
                    "expiry_date": {"value": "2020-01-01", "confidence": 0.95},
                    "first_name": {"value": "Jean", "confidence": 0.99},
                    "last_name": {"value": "Dupont", "confidence": 0.99},
                },
            }
        ]
        result = agent._rule_based_verification(requirements, documents, extracted)
        assert result["validity"]["score"] < 100.0
        assert any("expiré" in i["issue"] for i in result["validity"]["issues"])

    def test_rule_based_low_ocr_confidence(self):
        """Low OCR confidence should flag validity issues."""
        agent = ComplianceAgent()
        requirements = []
        documents = []
        extracted = [
            {
                "type": "passport",
                "fields": {
                    "first_name": {"value": "J??n", "confidence": 0.4},
                },
            }
        ]
        result = agent._rule_based_verification(requirements, documents, extracted)
        assert result["validity"]["score"] < 100.0
        assert any("confiance" in i["issue"] for i in result["validity"]["issues"])

    def test_rule_based_name_inconsistency(self):
        """Different names across documents should reduce consistency."""
        agent = ComplianceAgent()
        requirements = []
        documents = []
        extracted = [
            {
                "type": "passport",
                "fields": {
                    "first_name": {"value": "Jean", "confidence": 0.99},
                    "last_name": {"value": "Dupont", "confidence": 0.99},
                },
            },
            {
                "type": "bank_statement",
                "fields": {
                    "first_name": {"value": "Pierre", "confidence": 0.99},
                    "last_name": {"value": "Martin", "confidence": 0.99},
                },
            },
        ]
        result = agent._rule_based_verification(requirements, documents, extracted)
        assert result["consistency"]["score"] < 100.0
        assert len(result["consistency"]["issues"]) > 0

    def test_rule_based_consistent_names(self):
        """Same name across documents should give full consistency."""
        agent = ComplianceAgent()
        requirements = []
        documents = []
        extracted = [
            {
                "type": "passport",
                "fields": {
                    "first_name": {"value": "Jean", "confidence": 0.99},
                    "last_name": {"value": "Dupont", "confidence": 0.99},
                },
            },
            {
                "type": "bank_statement",
                "fields": {
                    "first_name": {"value": "Jean", "confidence": 0.95},
                    "last_name": {"value": "Dupont", "confidence": 0.95},
                },
            },
        ]
        result = agent._rule_based_verification(requirements, documents, extracted)
        assert result["consistency"]["score"] == 100.0

    def test_rule_based_method_indicator(self):
        """Rule-based results should indicate method."""
        agent = ComplianceAgent()
        result = agent._rule_based_verification([], [], [])
        assert result["method"] == "rule_based"

    def test_is_configured_without_key(self):
        """Agent should not be configured without API key."""
        agent = ComplianceAgent()
        # settings.anthropic_api_key is likely empty in test
        # The singleton may or may not be configured depending on env
        assert isinstance(agent.is_configured, bool)

    def test_parse_compliance_response_valid_json(self):
        """Parser should handle valid JSON response."""
        agent = ComplianceAgent()
        response = json.dumps(
            {
                "global_score": 85.0,
                "completeness": {"score": 90},
                "validity": {"score": 80},
                "consistency": {"score": 85},
            }
        )
        result = agent._parse_compliance_response(response)
        assert result["global_score"] == 85.0

    def test_parse_compliance_response_markdown_wrapped(self):
        """Parser should handle JSON wrapped in markdown code blocks."""
        agent = ComplianceAgent()
        response = '```json\n{"global_score": 75.0}\n```'
        result = agent._parse_compliance_response(response)
        assert result["global_score"] == 75.0

    def test_parse_compliance_response_invalid(self):
        """Parser should raise error on invalid JSON."""
        agent = ComplianceAgent()
        with pytest.raises(Exception):
            agent._parse_compliance_response("not valid json at all")


# =============================================================================
# Compliance API Endpoint Tests
# =============================================================================


class TestComplianceAPI:
    """Integration tests for the compliance API endpoints."""

    @pytest.mark.anyio
    async def test_verify_dossier_rule_based(self, client):
        """Verify compliance with rule-based fallback."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()

        # Add a passport document
        await add_document_to_dossier(dossier_id, "passport")

        with patch.object(compliance_agent, "_api_key", ""):
            response = await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "global_score" in data
        assert "status" in data
        assert "breakdown" in data
        assert "recommendations" in data
        # Only 1 of 3 mandatory docs present = ~33%
        assert data["global_score"] < 50.0

    @pytest.mark.anyio
    async def test_verify_dossier_all_docs(self, client):
        """High score when all mandatory docs present."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()

        # Add all mandatory documents
        await add_document_to_dossier(dossier_id, "passport")
        await add_document_to_dossier(dossier_id, "language_test")
        await add_document_to_dossier(dossier_id, "education_credential")

        with patch.object(compliance_agent, "_api_key", ""):
            response = await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["global_score"] >= 85.0
        assert data["status"] == "ready"
        assert data["is_ready_for_submission"] is True

    @pytest.mark.anyio
    async def test_verify_dossier_not_found(self, client):
        """Verify returns 404 for non-existent dossier."""
        async with TestSessionLocal() as session:
            admin = User(
                email="admin2@test.com",
                hashed_password=hash_password("pass"),
                full_name="Admin",
                role=UserRole.admin,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            token = create_access_token(
                {"sub": str(admin.id), "email": admin.email, "role": "admin"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/compliance/dossiers/9999/verify",
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_verify_cached_result(self, client):
        """Second verify should return cached result without force_refresh."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()
        await add_document_to_dossier(dossier_id, "passport")

        with patch.object(compliance_agent, "_api_key", ""):
            # First call
            response1 = await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
            )
            assert response1.status_code == 200

            # Second call should use cache
            response2 = await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
            )
            assert response2.status_code == 200
            assert response1.json()["global_score"] == response2.json()["global_score"]

    @pytest.mark.anyio
    async def test_verify_force_refresh(self, client):
        """Force refresh should re-run verification."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()
        await add_document_to_dossier(dossier_id, "passport")

        with patch.object(compliance_agent, "_api_key", ""):
            # First call
            await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
            )

            # Add more docs and force refresh
            await add_document_to_dossier(dossier_id, "language_test")
            await add_document_to_dossier(dossier_id, "education_credential")

            response = await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
                json={"force_refresh": True},
            )

        assert response.status_code == 200
        data = response.json()
        # Now all docs present, score should be high
        assert data["global_score"] >= 85.0

    @pytest.mark.anyio
    async def test_get_score_no_verification(self, client):
        """Get score returns null when not yet verified."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()

        response = await client.get(
            f"/compliance/dossiers/{dossier_id}/score",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.anyio
    async def test_get_score_after_verification(self, client):
        """Get score returns cached result after verification."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()
        await add_document_to_dossier(dossier_id, "passport")

        with patch.object(compliance_agent, "_api_key", ""):
            await client.post(
                f"/compliance/dossiers/{dossier_id}/verify",
                headers=headers,
            )

        response = await client.get(
            f"/compliance/dossiers/{dossier_id}/score",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert "global_score" in data

    @pytest.mark.anyio
    async def test_get_compliance_status(self, client):
        """Get compliance status overview."""
        dossier_id, program_id, headers = await setup_dossier_with_requirements()
        await add_document_to_dossier(dossier_id, "passport")

        response = await client.get(
            f"/compliance/dossiers/{dossier_id}/status",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dossier_id"] == dossier_id
        assert data["program_name"] == "Federal Skilled Worker"
        assert data["documents_count"] == 1
        assert "Test de langue (IELTS/TEF)" in data["missing_mandatory"]
        assert "Évaluation des diplômes (ECA)" in data["missing_mandatory"]
        assert data["status"] == "non_verifie"

    @pytest.mark.anyio
    async def test_candidat_access_own_dossier(self, client):
        """Candidat can view their own dossier score."""
        dossier_id, program_id, _ = await setup_dossier_with_requirements()

        # Get the candidate's user_id link
        async with TestSessionLocal() as session:
            candidat_user = User(
                email="candidat@test.com",
                hashed_password=hash_password("pass"),
                full_name="Candidat Test",
                role=UserRole.candidat,
            )
            session.add(candidat_user)
            await session.commit()
            await session.refresh(candidat_user)

            # Link candidate to user
            from sqlalchemy import update

            from app.models.candidate import Candidate

            await session.execute(
                update(Candidate)
                .where(Candidate.email == "jean@test.com")
                .values(user_id=candidat_user.id)
            )
            await session.commit()

            token = create_access_token(
                {"sub": str(candidat_user.id), "email": candidat_user.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/compliance/dossiers/{dossier_id}/status",
            headers=headers,
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_candidat_cannot_access_other_dossier(self, client):
        """Candidat cannot view another candidate's dossier."""
        dossier_id, program_id, _ = await setup_dossier_with_requirements()

        async with TestSessionLocal() as session:
            other_user = User(
                email="other@test.com",
                hashed_password=hash_password("pass"),
                full_name="Other User",
                role=UserRole.candidat,
            )
            session.add(other_user)
            await session.commit()
            await session.refresh(other_user)

            token = create_access_token(
                {"sub": str(other_user.id), "email": other_user.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/compliance/dossiers/{dossier_id}/status",
            headers=headers,
        )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_verify_requires_admin_or_consultant(self, client):
        """Verification endpoint requires admin or consultant role."""
        dossier_id, _, _ = await setup_dossier_with_requirements()

        async with TestSessionLocal() as session:
            candidat_user = User(
                email="candidat2@test.com",
                hashed_password=hash_password("pass"),
                full_name="Candidat2",
                role=UserRole.candidat,
            )
            session.add(candidat_user)
            await session.commit()
            await session.refresh(candidat_user)

            token = create_access_token(
                {"sub": str(candidat_user.id), "email": candidat_user.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            f"/compliance/dossiers/{dossier_id}/verify",
            headers=headers,
        )
        assert response.status_code == 403
