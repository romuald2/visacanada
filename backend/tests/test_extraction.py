"""Tests for OCR extraction system."""

import json
import pytest
from unittest.mock import AsyncMock, patch, PropertyMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Base, User, UserRole
from app.models.candidate import Candidate
from app.models.dossier import Dossier, DossierStatus
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.program import Program, ImmigrationProgram
from app.services.ocr_service import (
    AzureDocumentIntelligenceService,
    DocumentExtractionType,
    azure_ocr_service,
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


async def setup_document() -> tuple[int, dict]:
    """Create admin + document with S3 path. Return (document_id, headers)."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@ocr.com",
            hashed_password=hash_password("pass"),
            full_name="Admin OCR",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        candidate = Candidate(
            first_name="OCR", last_name="Test", email="ocr@test.com"
        )
        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="FSW",
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

        doc = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.passport,
            status=DocumentStatus.uploaded,
            file_name="passport.pdf",
            file_path_s3="documents/1/1/passport/abc_passport.pdf",
            mime_type="application/pdf",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        token = create_access_token(
            {"sub": str(admin.id), "email": admin.email, "role": "admin"}
        )
        return doc.id, {"Authorization": f"Bearer {token}"}


# Mock Azure DI passport response
MOCK_PASSPORT_RESPONSE = {
    "documents": [
        {
            "confidence": 0.95,
            "fields": {
                "FirstName": {"valueString": "Jean", "confidence": 0.98},
                "LastName": {"valueString": "Dupont", "confidence": 0.97},
                "DocumentNumber": {"valueString": "FR1234567", "confidence": 0.99},
                "DateOfBirth": {"valueDate": "1990-05-15", "confidence": 0.96},
                "DateOfExpiration": {"valueDate": "2028-03-20", "confidence": 0.95},
                "Nationality": {"valueString": "FRANCE", "confidence": 0.94},
                "Sex": {"valueString": "M", "confidence": 0.99},
            },
        }
    ]
}

MOCK_BANK_STATEMENT_RESPONSE = {
    "keyValuePairs": [
        {"key": {"content": "Solde final"}, "value": {"content": "15,432.50 CAD"}, "confidence": 0.9},
        {"key": {"content": "Numéro de compte"}, "value": {"content": "12345-678"}, "confidence": 0.95},
        {"key": {"content": "Titulaire"}, "value": {"content": "Jean Dupont"}, "confidence": 0.92},
        {"key": {"content": "Période"}, "value": {"content": "01/01/2026 - 31/03/2026"}, "confidence": 0.88},
    ],
    "pages": [
        {"lines": [{"content": "Relevé bancaire - Banque Nationale"}]}
    ],
}

MOCK_EMPLOYMENT_LETTER_RESPONSE = {
    "keyValuePairs": [
        {"key": {"content": "Poste"}, "value": {"content": "Développeur Senior"}, "confidence": 0.93},
        {"key": {"content": "Salaire annuel"}, "value": {"content": "95,000 CAD"}, "confidence": 0.91},
        {"key": {"content": "Date d'embauche"}, "value": {"content": "2022-03-01"}, "confidence": 0.89},
        {"key": {"content": "Employeur"}, "value": {"content": "TechCo Inc."}, "confidence": 0.95},
        {"key": {"content": "Heures/semaine"}, "value": {"content": "40"}, "confidence": 0.97},
    ],
    "pages": [
        {"lines": [{"content": "Lettre d'emploi - TechCo Inc."}]}
    ],
}


# --- Azure DI Parser Unit Tests ---


class TestAzureDocumentIntelligence:
    def test_parse_passport_result(self):
        service = AzureDocumentIntelligenceService()
        result = service._parse_passport_result(MOCK_PASSPORT_RESPONSE)

        assert result["type"] == "passport"
        assert result["confidence"] == 0.95
        assert result["fields"]["first_name"]["value"] == "Jean"
        assert result["fields"]["last_name"]["value"] == "Dupont"
        assert result["fields"]["document_number"]["value"] == "FR1234567"
        assert result["fields"]["date_of_birth"]["value"] == "1990-05-15"
        assert result["fields"]["nationality"]["value"] == "FRANCE"

    def test_parse_bank_statement_result(self):
        service = AzureDocumentIntelligenceService()
        result = service._parse_bank_statement_result(MOCK_BANK_STATEMENT_RESPONSE)

        assert result["type"] == "bank_statement"
        assert result["fields"]["balance"]["value"] == "15,432.50 CAD"
        assert result["fields"]["account_holder"]["value"] == "Jean Dupont"
        assert "Relevé bancaire" in result["raw_text"]

    def test_parse_employment_letter_result(self):
        service = AzureDocumentIntelligenceService()
        result = service._parse_employment_letter_result(MOCK_EMPLOYMENT_LETTER_RESPONSE)

        assert result["type"] == "employment_letter"
        assert result["fields"]["job_title"]["value"] == "Développeur Senior"
        assert result["fields"]["salary"]["value"] == "95,000 CAD"
        assert result["fields"]["employer_name"]["value"] == "TechCo Inc."
        assert result["fields"]["hours_per_week"]["value"] == "40"

    def test_parse_passport_empty_documents(self):
        service = AzureDocumentIntelligenceService()
        result = service._parse_passport_result({"documents": []})

        assert result["type"] == "passport"
        assert result["fields"] == {}
        assert result["confidence"] == 0.0

    def test_parse_generic_result(self):
        service = AzureDocumentIntelligenceService()
        mock_result = {
            "keyValuePairs": [
                {"key": {"content": "Name"}, "value": {"content": "Test"}},
            ],
            "pages": [{"lines": [{"content": "Hello World"}]}],
        }
        result = service._parse_generic_result(mock_result)

        assert result["type"] == "generic"
        assert len(result["key_value_pairs"]) == 1
        assert "Hello World" in result["raw_text"]


# --- Extraction API Tests ---


class TestExtractionAPI:
    @patch("app.api.extraction._fetch_file_from_s3")
    @patch("app.api.extraction.azure_ocr_service")
    async def test_extract_passport(self, mock_azure, mock_fetch, client: AsyncClient):
        mock_fetch.return_value = b"fake pdf content"
        mock_azure.is_configured = True
        mock_azure.extract_document = AsyncMock(return_value={
            "type": "passport",
            "fields": {"first_name": {"value": "Jean", "confidence": 0.98}},
            "confidence": 0.95,
        })

        doc_id, headers = await setup_document()

        response = await client.post(
            f"/extraction/{doc_id}/extract",
            json={"extraction_type": "passport"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "azure_document_intelligence"
        assert data["extracted_data"]["type"] == "passport"

    @patch("app.api.extraction._fetch_file_from_s3")
    @patch("app.api.extraction.azure_ocr_service")
    @patch("app.api.extraction.tesseract_service")
    async def test_extract_fallback_tesseract(
        self, mock_tess, mock_azure, mock_fetch, client: AsyncClient
    ):
        mock_fetch.return_value = b"fake image content"
        mock_azure.is_configured = False
        mock_tess.is_available = True
        mock_tess.extract_text = AsyncMock(return_value={
            "type": "tesseract_fallback",
            "fields": {},
            "raw_text": "PASSPORT\nJean Dupont\nFR1234567",
            "confidence": 0.6,
            "method": "tesseract",
        })

        doc_id, headers = await setup_document()

        response = await client.post(
            f"/extraction/{doc_id}/extract",
            json={"extraction_type": "generic"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "tesseract"

    @patch("app.api.extraction.azure_ocr_service")
    @patch("app.api.extraction.tesseract_service")
    async def test_extract_no_service_available(
        self, mock_tess, mock_azure, client: AsyncClient
    ):
        mock_azure.is_configured = False
        mock_tess.is_available = False

        doc_id, headers = await setup_document()

        response = await client.post(
            f"/extraction/{doc_id}/extract",
            json={"extraction_type": "passport"},
            headers=headers,
        )

        assert response.status_code == 503

    async def test_extract_document_not_found(self, client: AsyncClient):
        async with TestSessionLocal() as session:
            admin = User(
                email="admin2@ocr.com",
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
            "/extraction/999/extract",
            json={"extraction_type": "passport"},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_get_extracted_data(self, client: AsyncClient):
        doc_id, headers = await setup_document()

        # Set extracted data on document
        async with TestSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = result.scalar_one()
            doc.extracted_data = json.dumps({
                "type": "passport",
                "fields": {"first_name": {"value": "Jean"}},
            })
            await session.commit()

        response = await client.get(
            f"/extraction/{doc_id}/extracted-data", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_data"]["type"] == "passport"
        assert data["extracted_data"]["fields"]["first_name"]["value"] == "Jean"

    async def test_get_extracted_data_empty(self, client: AsyncClient):
        doc_id, headers = await setup_document()

        response = await client.get(
            f"/extraction/{doc_id}/extracted-data", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_data"] is None

    async def test_update_extracted_data_manual_correction(self, client: AsyncClient):
        doc_id, headers = await setup_document()

        response = await client.put(
            f"/extraction/{doc_id}/extracted-data",
            json={
                "extracted_data": {
                    "type": "passport",
                    "fields": {
                        "first_name": {"value": "Jean-Pierre", "confidence": 1.0},
                        "last_name": {"value": "Dupont", "confidence": 1.0},
                    },
                },
                "notes": "Correction: prénom composé non détecté par OCR",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_data"]["fields"]["first_name"]["value"] == "Jean-Pierre"
        assert "_manual_correction" in data["extracted_data"]

    @patch("app.api.extraction._fetch_file_from_s3")
    @patch("app.api.extraction.azure_ocr_service")
    async def test_extract_populates_expiry(self, mock_azure, mock_fetch, client: AsyncClient):
        mock_fetch.return_value = b"fake pdf content"
        mock_azure.is_configured = True
        mock_azure.extract_document = AsyncMock(return_value={
            "type": "passport",
            "fields": {"expiry_date": {"value": "2029-08-15", "confidence": 0.96}},
            "confidence": 0.95,
        })

        doc_id, headers = await setup_document()
        resp = await client.post(
            f"/extraction/{doc_id}/extract",
            json={"extraction_type": "passport"},
            headers=headers,
        )
        assert resp.status_code == 200

        async with TestSessionLocal() as session:
            doc = (
                await session.execute(select(Document).where(Document.id == doc_id))
            ).scalar_one()
            assert doc.expires_at is not None
            assert doc.expires_at.year == 2029
            assert doc.expires_at.month == 8

    async def test_manual_correction_updates_expiry(self, client: AsyncClient):
        # Use a language_test doc so expiry is derived from issue date.
        async with TestSessionLocal() as session:
            admin = User(
                email="admin3@ocr.com",
                hashed_password=hash_password("pass"),
                full_name="Admin",
                role=UserRole.admin,
            )
            candidate = Candidate(first_name="L", last_name="T", email="lt@ocr.com")
            program = Program(
                code=ImmigrationProgram.express_entry_fsw,
                name="FSW",
                category="Express Entry",
                is_active=True,
            )
            session.add_all([admin, candidate, program])
            await session.commit()
            await session.refresh(admin)
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
            doc = Document(
                dossier_id=dossier.id,
                document_type=DocumentType.language_test,
                status=DocumentStatus.uploaded,
                file_name="ielts.pdf",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id
            token = create_access_token(
                {"sub": str(admin.id), "email": admin.email, "role": "admin"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/extraction/{doc_id}/extracted-data",
            json={
                "extracted_data": {
                    "type": "language_test",
                    "fields": {"issue_date": {"value": "2025-06-01", "confidence": 1.0}},
                }
            },
            headers=headers,
        )
        assert resp.status_code == 200

        async with TestSessionLocal() as session:
            doc = (
                await session.execute(select(Document).where(Document.id == doc_id))
            ).scalar_one()
            # 2025-06-01 + 730 days = 2027-05-31/06-01 window
            assert doc.expires_at is not None
            assert doc.expires_at.year == 2027

    async def test_update_extracted_data_forbidden_for_candidat(self, client: AsyncClient):
        doc_id, _ = await setup_document()

        async with TestSessionLocal() as session:
            candidat = User(
                email="cand@ocr.com",
                hashed_password=hash_password("pass"),
                full_name="Cand",
                role=UserRole.candidat,
            )
            session.add(candidat)
            await session.commit()
            await session.refresh(candidat)
            token = create_access_token(
                {"sub": str(candidat.id), "email": candidat.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.put(
            f"/extraction/{doc_id}/extracted-data",
            json={"extracted_data": {"type": "passport", "fields": {}}},
            headers=headers,
        )

        assert response.status_code == 403
