"""Tests for secure document upload and storage system."""

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.dossier import Dossier, DossierStatus
from app.models.program import ImmigrationProgram, Program
from app.models.user import Base, User, UserRole
from app.services.s3_storage import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    S3StorageService,
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


async def setup_dossier() -> tuple[int, dict]:
    """Create admin, candidate, program, dossier. Return (dossier_id, headers)."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@upload.com",
            hashed_password=hash_password("pass"),
            full_name="Admin Upload",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        candidate = Candidate(first_name="Upload", last_name="Test", email="upload@test.com")
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

        token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "admin"})
        return dossier.id, {"Authorization": f"Bearer {token}"}


# --- S3 Service Unit Tests ---


class TestS3StorageService:
    def test_generate_s3_key(self):
        service = S3StorageService()
        key = service._generate_s3_key(1, 2, "passport", "my_passport.pdf")

        assert key.startswith("documents/1/2/passport/")
        assert "my_passport.pdf" in key

    def test_generate_s3_key_spaces_replaced(self):
        service = S3StorageService()
        key = service._generate_s3_key(1, 2, "passport", "my passport scan.pdf")

        assert " " not in key
        assert "my_passport_scan.pdf" in key

    def test_generate_archive_key(self):
        service = S3StorageService()
        archive = service._generate_archive_key("documents/1/2/passport/file.pdf")

        assert archive.startswith("archived/")
        assert "documents/1/2/passport/file.pdf" in archive

    def test_allowed_mime_types(self):
        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "image/png" in ALLOWED_MIME_TYPES
        assert "application/msword" in ALLOWED_MIME_TYPES
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in ALLOWED_MIME_TYPES
        )
        # Not allowed
        assert "application/zip" not in ALLOWED_MIME_TYPES
        assert "text/plain" not in ALLOWED_MIME_TYPES


# --- Upload API Tests ---


class TestUploadAPI:
    @patch("app.api.upload.s3_storage")
    async def test_upload_pdf(self, mock_s3, client: AsyncClient):
        mock_s3.upload_file = AsyncMock(
            return_value={
                "s3_key": "documents/1/1/passport/abc_test.pdf",
                "file_size": 1024,
                "mime_type": "application/pdf",
                "bucket": "test-bucket",
            }
        )

        dossier_id, headers = await setup_dossier()
        pdf_content = b"%PDF-1.4 fake pdf content" * 100

        response = await client.post(
            f"/upload/{dossier_id}?document_type=passport",
            files={"file": ("passport.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "passport.pdf"
        assert data["status"] == "uploaded"
        assert data["mime_type"] == "application/pdf"

    async def test_upload_invalid_mime_type(self, client: AsyncClient):
        dossier_id, headers = await setup_dossier()

        response = await client.post(
            f"/upload/{dossier_id}?document_type=other",
            files={"file": ("virus.exe", io.BytesIO(b"malware"), "application/x-executable")},
            headers=headers,
        )

        assert response.status_code == 400
        assert "non autorisé" in response.json()["detail"]

    async def test_upload_file_too_large(self, client: AsyncClient):
        dossier_id, headers = await setup_dossier()
        large_content = b"x" * (MAX_FILE_SIZE_BYTES + 1)

        response = await client.post(
            f"/upload/{dossier_id}?document_type=passport",
            files={"file": ("big.pdf", io.BytesIO(large_content), "application/pdf")},
            headers=headers,
        )

        assert response.status_code == 400
        assert "volumineux" in response.json()["detail"]

    async def test_upload_empty_file(self, client: AsyncClient):
        dossier_id, headers = await setup_dossier()

        response = await client.post(
            f"/upload/{dossier_id}?document_type=passport",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            headers=headers,
        )

        assert response.status_code == 400
        assert "vide" in response.json()["detail"]

    async def test_upload_dossier_not_found(self, client: AsyncClient):
        _, headers = await setup_dossier()

        response = await client.post(
            "/upload/999?document_type=passport",
            files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")},
            headers=headers,
        )

        assert response.status_code == 404

    @patch("app.api.upload.s3_storage")
    async def test_view_document_url(self, mock_s3, client: AsyncClient):
        mock_s3.generate_presigned_url = AsyncMock(
            return_value="https://s3.amazonaws.com/bucket/key?signature=abc"
        )

        dossier_id, headers = await setup_dossier()

        # Create a document record
        async with TestSessionLocal() as session:
            doc = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.passport,
                status=DocumentStatus.uploaded,
                file_name="test.pdf",
                file_path_s3="documents/1/1/passport/test.pdf",
                mime_type="application/pdf",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        response = await client.get(f"/upload/{doc_id}/view", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["expires_in"] == 300
        assert data["content_type"] == "application/pdf"

    @patch("app.api.upload.s3_storage")
    async def test_download_document_url(self, mock_s3, client: AsyncClient):
        mock_s3.generate_presigned_url = AsyncMock(
            return_value="https://s3.amazonaws.com/bucket/key?signature=xyz"
        )

        dossier_id, headers = await setup_dossier()

        async with TestSessionLocal() as session:
            doc = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.bank_statement,
                status=DocumentStatus.uploaded,
                file_name="bank.pdf",
                file_path_s3="documents/1/1/bank/bank.pdf",
                mime_type="application/pdf",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        response = await client.get(f"/upload/{doc_id}/download", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "bank.pdf"

    @patch("app.api.upload.s3_storage")
    async def test_soft_delete_document(self, mock_s3, client: AsyncClient):
        mock_s3.soft_delete = AsyncMock(return_value="archived/20260727/documents/1/1/p/f.pdf")

        dossier_id, headers = await setup_dossier()

        async with TestSessionLocal() as session:
            doc = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.photo,
                status=DocumentStatus.uploaded,
                file_name="photo.jpg",
                file_path_s3="documents/1/1/photo/photo.jpg",
                mime_type="image/jpeg",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        response = await client.delete(f"/upload/{doc_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "archivé" in data["message"]

    async def test_view_document_not_found(self, client: AsyncClient):
        _, headers = await setup_dossier()

        response = await client.get("/upload/999/view", headers=headers)

        assert response.status_code == 404
