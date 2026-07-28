"""Tests for the candidate self-service portal."""

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.dossier import Dossier, DossierStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from app.models.program import ImmigrationProgram, Program
from app.models.program_requirement import ProgramRequirement, RequirementPriority
from app.models.user import Base, User, UserRole

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


def _auth(user: User) -> dict:
    token = create_access_token(
        {"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


async def setup_candidate_with_dossier():
    """Create a candidat user + candidate profile + program + dossier + docs."""
    async with TestSessionLocal() as session:
        cand_user = User(
            email="cand@portal.com",
            hashed_password=hash_password("pass"),
            full_name="Cand Portal",
            role=UserRole.candidat,
        )
        session.add(cand_user)
        await session.commit()
        await session.refresh(cand_user)

        candidate = Candidate(
            user_id=cand_user.id,
            first_name="Ada",
            last_name="Lovelace",
            email="cand@portal.com",
            nationality="GB",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="Express Entry FSW",
            category="express_entry",
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.en_cours,
            compliance_score=87.5,
            reference_number="REF-001",
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        # Provided doc
        doc = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.passport,
            status=DocumentStatus.verified,
            file_name="passport.pdf",
            compliance_score=95.0,
            fraud_score=2.0,
        )
        session.add(doc)

        # Requirements: passport (provided) + language_test (missing)
        session.add(
            ProgramRequirement(
                program_id=program.id,
                document_type="passport",
                document_name="Passeport",
                priority=RequirementPriority.mandatory,
            )
        )
        session.add(
            ProgramRequirement(
                program_id=program.id,
                document_type="language_test",
                document_name="Test de langue",
                priority=RequirementPriority.mandatory,
            )
        )

        # Notification for candidate
        session.add(
            Notification(
                recipient_id=cand_user.id,
                dossier_id=dossier.id,
                notification_type=NotificationType.status_change,
                channel=NotificationChannel.dashboard,
                title="Dossier mis a jour",
                message="Votre dossier est en cours.",
            )
        )
        await session.commit()

        return {
            "user": cand_user,
            "candidate_id": candidate.id,
            "dossier_id": dossier.id,
            "headers": _auth(cand_user),
        }


async def create_admin() -> dict:
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@portal.com",
            hashed_password=hash_password("pass"),
            full_name="Admin",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return {"headers": _auth(admin)}


# =============================================================================
# Access control
# =============================================================================


class TestPortalAccess:
    async def test_admin_cannot_access_portal(self, client):
        admin = await create_admin()
        resp = await client.get("/portal/me", headers=admin["headers"])
        assert resp.status_code == 403

    async def test_requires_auth(self, client):
        resp = await client.get("/portal/me")
        assert resp.status_code in (401, 403)

    async def test_candidat_without_profile_404(self, client):
        async with TestSessionLocal() as session:
            u = User(
                email="orphan@portal.com",
                hashed_password=hash_password("pass"),
                full_name="Orphan",
                role=UserRole.candidat,
            )
            session.add(u)
            await session.commit()
            await session.refresh(u)
            headers = _auth(u)
        resp = await client.get("/portal/me", headers=headers)
        assert resp.status_code == 404


# =============================================================================
# Read views
# =============================================================================


class TestPortalViews:
    async def test_get_me(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.get("/portal/me", headers=ctx["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "Ada"
        # Internal scores must never be present on profile
        assert "compliance_score" not in data

    async def test_list_dossiers_has_progress_no_scores(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.get("/portal/dossiers", headers=ctx["headers"])
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        d = items[0]
        assert d["progress"] == 30  # en_cours
        assert d["status_label"]["fr"] == "En cours"
        assert d["status_label"]["en"] == "In progress"
        assert "compliance_score" not in d
        assert "compliance_details" not in d

    async def test_get_single_dossier(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.get(
            f"/portal/dossiers/{ctx['dossier_id']}", headers=ctx["headers"]
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reference_number"] == "REF-001"
        assert data["program"]["category"] == "express_entry"
        assert "compliance_score" not in data

    async def test_cannot_access_other_dossier(self, client):
        ctx = await setup_candidate_with_dossier()
        # Create a second candidate's dossier
        async with TestSessionLocal() as session:
            other_user = User(
                email="other@portal.com",
                hashed_password=hash_password("pass"),
                full_name="Other",
                role=UserRole.candidat,
            )
            session.add(other_user)
            await session.commit()
            await session.refresh(other_user)
            other_cand = Candidate(
                user_id=other_user.id,
                first_name="Bob",
                last_name="Smith",
                email="other@portal.com",
            )
            session.add(other_cand)
            await session.commit()
            await session.refresh(other_cand)
            prog = (await session.execute(
                __import__("sqlalchemy").select(Program)
            )).scalars().first()
            other_dossier = Dossier(
                candidate_id=other_cand.id,
                program_id=prog.id,
                status=DossierStatus.nouveau,
            )
            session.add(other_dossier)
            await session.commit()
            await session.refresh(other_dossier)
            other_id = other_dossier.id

        resp = await client.get(
            f"/portal/dossiers/{other_id}", headers=ctx["headers"]
        )
        assert resp.status_code == 404

    async def test_documents_provided_and_missing(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.get(
            f"/portal/dossiers/{ctx['dossier_id']}/documents",
            headers=ctx["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provided_count"] == 1
        assert data["missing_count"] == 1
        assert data["provided"][0]["document_type"] == "passport"
        assert data["missing"][0]["document_type"] == "language_test"
        # No internal scores leaked on provided documents
        assert "compliance_score" not in data["provided"][0]
        assert "fraud_score" not in data["provided"][0]

    async def test_notifications(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.get("/portal/notifications", headers=ctx["headers"])
        assert resp.status_code == 200
        notifs = resp.json()
        assert len(notifs) == 1
        assert notifs[0]["is_read"] is False

    async def test_mark_notification_read(self, client):
        ctx = await setup_candidate_with_dossier()
        listing = await client.get("/portal/notifications", headers=ctx["headers"])
        nid = listing.json()[0]["id"]
        resp = await client.post(
            f"/portal/notifications/{nid}/read", headers=ctx["headers"]
        )
        assert resp.status_code == 200
        after = await client.get("/portal/notifications", headers=ctx["headers"])
        assert after.json()[0]["is_read"] is True

    async def test_cannot_mark_others_notification(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.post(
            "/portal/notifications/9999/read", headers=ctx["headers"]
        )
        assert resp.status_code == 404


# =============================================================================
# Self-upload
# =============================================================================


class TestPortalUpload:
    async def test_upload_document(self, client, monkeypatch):
        ctx = await setup_candidate_with_dossier()

        async def fake_upload(**kwargs):
            return {"s3_key": "candidates/1/dossiers/1/language_test/x.pdf"}

        monkeypatch.setattr(
            "app.api.portal.s3_storage.upload_file", fake_upload
        )

        resp = await client.post(
            f"/portal/dossiers/{ctx['dossier_id']}/documents",
            headers=ctx["headers"],
            params={"document_type": "language_test"},
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_name"] == "test.pdf"
        assert data["status"] == "uploaded"

    async def test_upload_rejects_bad_mime(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.post(
            f"/portal/dossiers/{ctx['dossier_id']}/documents",
            headers=ctx["headers"],
            params={"document_type": "language_test"},
            files={"file": ("test.exe", b"MZ", "application/x-msdownload")},
        )
        assert resp.status_code == 400

    async def test_upload_to_unowned_dossier_404(self, client):
        ctx = await setup_candidate_with_dossier()
        resp = await client.post(
            "/portal/dossiers/9999/documents",
            headers=ctx["headers"],
            params={"document_type": "language_test"},
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 404
