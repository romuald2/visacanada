"""Tests for admin dashboard API."""

import pytest
from datetime import datetime, timedelta, timezone

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
from app.models.whatsapp_notification import WhatsAppNotification, NotificationStatus

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
    """Create admin user, return auth headers."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@dashboard.com",
            hashed_password=hash_password("pass"),
            full_name="Admin Dashboard",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(
            {"sub": str(admin.id), "email": admin.email, "role": "admin"}
        )
        return {"headers": {"Authorization": f"Bearer {token}"}, "user_id": admin.id}


async def create_consultant() -> dict:
    """Create consultant user, return auth headers."""
    async with TestSessionLocal() as session:
        consultant = User(
            email="consultant@dashboard.com",
            hashed_password=hash_password("pass"),
            full_name="Consultant",
            role=UserRole.consultant,
        )
        session.add(consultant)
        await session.commit()
        await session.refresh(consultant)
        token = create_access_token(
            {"sub": str(consultant.id), "email": consultant.email, "role": "consultant"}
        )
        return {"headers": {"Authorization": f"Bearer {token}"}, "user_id": consultant.id}


async def create_candidat() -> dict:
    """Create candidat user, return auth headers."""
    async with TestSessionLocal() as session:
        candidat = User(
            email="candidat@dashboard.com",
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
        return {"headers": {"Authorization": f"Bearer {token}"}, "user_id": candidat.id}


async def seed_test_data(admin_id: int):
    """Seed dossiers, documents, candidates, programs for dashboard tests."""
    async with TestSessionLocal() as session:
        # Program
        program = Program(
            name="Express Entry",
            code=ImmigrationProgram.express_entry_fsw,
            category="express_entry",
            description="Federal skilled worker",
            is_active=True,
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)

        # Candidate
        candidate = Candidate(
            user_id=admin_id,
            first_name="Jean",
            last_name="Dupont",
            email="jean@test.com",
            nationality="FR",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        # Dossiers with various statuses
        statuses = [
            DossierStatus.nouveau,
            DossierStatus.en_cours,
            DossierStatus.en_cours,
            DossierStatus.documents_manquants,
            DossierStatus.soumis,
        ]
        dossier_ids = []
        for s in statuses:
            d = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                assigned_to=admin_id,
                status=s,
                compliance_score=75.0 if s != DossierStatus.nouveau else None,
            )
            session.add(d)
            await session.commit()
            await session.refresh(d)
            dossier_ids.append(d.id)

        # Document expiring in 10 days
        now = datetime.now(timezone.utc)
        doc_expiring = Document(
            dossier_id=dossier_ids[0],
            document_type=DocumentType.passport,
            status=DocumentStatus.verified,
            file_name="passport.pdf",
            expires_at=now + timedelta(days=10),
        )
        session.add(doc_expiring)

        # Document already expired
        doc_expired = Document(
            dossier_id=dossier_ids[1],
            document_type=DocumentType.medical_exam,
            status=DocumentStatus.verified,
            file_name="medical.pdf",
            expires_at=now - timedelta(days=5),
        )
        session.add(doc_expired)

        # Normal document (no expiry)
        doc_normal = Document(
            dossier_id=dossier_ids[2],
            document_type=DocumentType.bank_statement,
            status=DocumentStatus.verified,
            file_name="bank.pdf",
        )
        session.add(doc_normal)

        # Notification
        notif = WhatsAppNotification(
            user_id=admin_id,
            event_type="ircc_email_detected",
            to_number="+15551234567",
            message="Test notification",
            status=NotificationStatus.not_configured,
            channel=None,
        )
        session.add(notif)
        await session.commit()

        return {
            "program_id": program.id,
            "candidate_id": candidate.id,
            "dossier_ids": dossier_ids,
        }


# =============================================================================
# Dashboard API Tests
# =============================================================================


class TestDashboardOverview:
    """Tests for GET /dashboard/overview."""

    @pytest.mark.anyio
    async def test_overview_empty(self, client):
        """Overview returns zeros when no data."""
        admin = await create_admin()
        response = await client.get("/dashboard/overview", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["total_dossiers"] == 0
        assert data["total_candidates"] == 0
        assert data["average_compliance_score"] is None
        assert data["by_status"] == {}

    @pytest.mark.anyio
    async def test_overview_with_data(self, client):
        """Overview returns correct counts."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get("/dashboard/overview", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["total_dossiers"] == 5
        assert data["total_candidates"] == 1
        assert data["average_compliance_score"] == 75.0
        assert data["by_status"]["en_cours"] == 2
        assert data["by_status"]["nouveau"] == 1

    @pytest.mark.anyio
    async def test_overview_candidat_forbidden(self, client):
        """Candidat cannot access dashboard."""
        candidat = await create_candidat()
        response = await client.get("/dashboard/overview", headers=candidat["headers"])
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_overview_consultant_allowed(self, client):
        """Consultant can access dashboard."""
        consultant = await create_consultant()
        response = await client.get("/dashboard/overview", headers=consultant["headers"])
        assert response.status_code == 200
# PLACEHOLDER_URGENT


class TestDashboardUrgentActions:
    """Tests for GET /dashboard/urgent-actions."""

    @pytest.mark.anyio
    async def test_urgent_actions_empty(self, client):
        """No urgent actions when no data."""
        admin = await create_admin()
        response = await client.get("/dashboard/urgent-actions", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["expiring_documents"] == []
        assert data["expired_documents"] == []
        assert data["dossiers_missing_documents"] == []

    @pytest.mark.anyio
    async def test_urgent_actions_with_data(self, client):
        """Returns expiring/expired docs and missing doc dossiers."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get("/dashboard/urgent-actions", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        # 1 doc expiring within 30 days
        assert len(data["expiring_documents"]) == 1
        assert data["expiring_documents"][0]["document_type"] == "passport"
        assert data["expiring_documents"][0]["days_remaining"] <= 10
        # 1 expired doc
        assert len(data["expired_documents"]) == 1
        assert data["expired_documents"][0]["document_type"] == "medical_exam"
        # 1 dossier with missing documents status
        assert len(data["dossiers_missing_documents"]) == 1


class TestDashboardRecentNotifications:
    """Tests for GET /dashboard/recent-notifications."""

    @pytest.mark.anyio
    async def test_recent_notifications_empty(self, client):
        """Empty list when no notifications."""
        admin = await create_admin()
        response = await client.get("/dashboard/recent-notifications", headers=admin["headers"])
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_recent_notifications_with_data(self, client):
        """Returns stored notifications."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get("/dashboard/recent-notifications", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "ircc_email_detected"

    @pytest.mark.anyio
    async def test_recent_notifications_limit(self, client):
        """Respects limit parameter."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get(
            "/dashboard/recent-notifications?limit=1", headers=admin["headers"]
        )
        assert response.status_code == 200
        assert len(response.json()) <= 1


class TestDashboardRecentDossiers:
    """Tests for GET /dashboard/recent-dossiers."""

    @pytest.mark.anyio
    async def test_recent_dossiers(self, client):
        """Returns recent dossiers."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get("/dashboard/recent-dossiers", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.anyio
    async def test_recent_dossiers_filter_status(self, client):
        """Filter by status."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get(
            "/dashboard/recent-dossiers?status=en_cours", headers=admin["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(d["status"] == "en_cours" for d in data)

    @pytest.mark.anyio
    async def test_recent_dossiers_filter_program(self, client):
        """Filter by program_id."""
        admin = await create_admin()
        seed_data = await seed_test_data(admin["user_id"])

        response = await client.get(
            f"/dashboard/recent-dossiers?program_id={seed_data['program_id']}",
            headers=admin["headers"],
        )
        assert response.status_code == 200
        assert len(response.json()) == 5

    @pytest.mark.anyio
    async def test_recent_dossiers_filter_nonexistent_program(self, client):
        """Filter by non-existent program returns empty."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get(
            "/dashboard/recent-dossiers?program_id=999", headers=admin["headers"]
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_recent_dossiers_limit(self, client):
        """Respects limit."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get(
            "/dashboard/recent-dossiers?limit=2", headers=admin["headers"]
        )
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestDashboardStatsByProgram:
    """Tests for GET /dashboard/stats-by-program."""

    @pytest.mark.anyio
    async def test_stats_by_program(self, client):
        """Returns per-program statistics."""
        admin = await create_admin()
        await seed_test_data(admin["user_id"])

        response = await client.get("/dashboard/stats-by-program", headers=admin["headers"])
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["program_name"] == "Express Entry"
        assert data[0]["total_dossiers"] == 5
        assert data[0]["average_score"] == 75.0

    @pytest.mark.anyio
    async def test_stats_by_program_empty(self, client):
        """Empty when no programs."""
        admin = await create_admin()
        response = await client.get("/dashboard/stats-by-program", headers=admin["headers"])
        assert response.status_code == 200
        assert response.json() == []
