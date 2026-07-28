"""Tests for analytics and reporting."""

from datetime import datetime, timedelta, timezone

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.dossier import Dossier, DossierStatus
from app.models.program import ImmigrationProgram, Program
from app.models.user import Base, User, UserRole
from app.services.analytics_service import AnalyticsService

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


async def create_admin() -> dict:
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@an.com",
            hashed_password=hash_password("pass"),
            full_name="Admin",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return {"headers": _auth(admin)}


async def create_candidat() -> dict:
    async with TestSessionLocal() as session:
        u = User(
            email="c@an.com",
            hashed_password=hash_password("pass"),
            full_name="Cand",
            role=UserRole.candidat,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return {"headers": _auth(u)}


async def seed_data():
    """Two programs; several dossiers with varied statuses and dates."""
    async with TestSessionLocal() as session:
        cand = Candidate(first_name="A", last_name="B", email="ab@an.com")
        session.add(cand)
        await session.commit()
        await session.refresh(cand)

        prog1 = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="EE FSW",
            category="express_entry",
            government_fee=1500.0,
            processing_time_days=180,
        )
        prog2 = Program(
            code=ImmigrationProgram.study_permit,
            name="Study Permit",
            category="study",
            government_fee=500.0,
            processing_time_days=90,
        )
        session.add_all([prog1, prog2])
        await session.commit()
        await session.refresh(prog1)
        await session.refresh(prog2)

        now = datetime.now(timezone.utc)
        dossiers = [
            # prog1: 2 approved, 1 refused, 1 active
            Dossier(candidate_id=cand.id, program_id=prog1.id,
                    status=DossierStatus.approuve,
                    created_at=now - timedelta(days=200),
                    decision_at=now - timedelta(days=20)),
            Dossier(candidate_id=cand.id, program_id=prog1.id,
                    status=DossierStatus.approuve,
                    created_at=now - timedelta(days=150),
                    decision_at=now - timedelta(days=10)),
            Dossier(candidate_id=cand.id, program_id=prog1.id,
                    status=DossierStatus.refuse,
                    created_at=now - timedelta(days=160),
                    decision_at=now - timedelta(days=30)),
            Dossier(candidate_id=cand.id, program_id=prog1.id,
                    status=DossierStatus.en_cours,
                    created_at=now - timedelta(days=30)),
            # prog2: 1 approved, 1 active
            Dossier(candidate_id=cand.id, program_id=prog2.id,
                    status=DossierStatus.approuve,
                    created_at=now - timedelta(days=100),
                    decision_at=now - timedelta(days=40)),
            Dossier(candidate_id=cand.id, program_id=prog2.id,
                    status=DossierStatus.nouveau,
                    created_at=now - timedelta(days=5)),
        ]
        session.add_all(dossiers)
        await session.commit()
        return {"prog1_id": prog1.id, "prog2_id": prog2.id}


# =============================================================================
# Service unit tests
# =============================================================================


class TestAnalyticsService:
    async def test_overview(self):
        await seed_data()
        svc = AnalyticsService()
        async with TestSessionLocal() as session:
            data = await svc.overview(session)
        assert data["total"] == 6
        assert data["approved"] == 3
        assert data["refused"] == 1
        assert data["active"] == 2

    async def test_success_rate(self):
        await seed_data()
        svc = AnalyticsService()
        async with TestSessionLocal() as session:
            rows = await svc.success_rate_by_program(session)
        by_name = {r["program_name"]: r for r in rows}
        # prog1: 2 approved / (2+1 decided) = 66.7%
        assert by_name["EE FSW"]["success_rate"] == 66.7
        # prog2: 1 approved / 1 decided = 100%
        assert by_name["Study Permit"]["success_rate"] == 100.0

    async def test_processing_time(self):
        await seed_data()
        svc = AnalyticsService()
        async with TestSessionLocal() as session:
            data = await svc.avg_processing_time(session)
        assert data["overall_avg_days"] is not None
        assert data["decided_count"] == 4

    async def test_revenue_by_month(self):
        await seed_data()
        svc = AnalyticsService()
        async with TestSessionLocal() as session:
            data = await svc.revenue_by_period(session, "month")
        # 4 prog1 dossiers * 1500 + 2 prog2 * 500 = 6000 + 1000 = 7000
        assert data["total_revenue"] == 7000.0
        assert len(data["series"]) >= 1

    async def test_workload_forecast(self):
        await seed_data()
        svc = AnalyticsService()
        async with TestSessionLocal() as session:
            data = await svc.workload_forecast(session)
        assert data["active_dossiers"] == 2
        assert len(data["expected_decisions"]) >= 1

    def test_to_csv(self):
        svc = AnalyticsService()
        rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        csv_bytes = svc.to_csv(rows)
        text = csv_bytes.decode("utf-8")
        assert "a,b" in text
        assert "1,2" in text

    def test_to_csv_empty(self):
        svc = AnalyticsService()
        assert svc.to_csv([]) == b""

    def test_report_pdf(self):
        svc = AnalyticsService()
        pdf = svc.report_pdf(
            "Test", [{"heading": "S1", "rows": [{"x": 1}]}]
        )
        assert pdf[:4] == b"%PDF"


# =============================================================================
# API integration tests
# =============================================================================


class TestAnalyticsAPI:
    async def test_overview(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get("/analytics/overview", headers=admin["headers"])
        assert resp.status_code == 200
        assert resp.json()["total"] == 6

    async def test_success_rate(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get("/analytics/success-rate", headers=admin["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_processing_time(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get(
            "/analytics/processing-time", headers=admin["headers"]
        )
        assert resp.status_code == 200

    async def test_revenue(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get(
            "/analytics/revenue?period=year", headers=admin["headers"]
        )
        assert resp.status_code == 200
        assert resp.json()["period"] == "year"

    async def test_workload_forecast(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get(
            "/analytics/workload-forecast", headers=admin["headers"]
        )
        assert resp.status_code == 200

    async def test_export_csv(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get(
            "/analytics/export/csv?report=success-rate", headers=admin["headers"]
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert b"program_name" in resp.content

    async def test_export_pdf(self, client):
        admin = await create_admin()
        await seed_data()
        resp = await client.get("/analytics/export/pdf", headers=admin["headers"])
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    async def test_rbac_candidat_forbidden(self, client):
        cand = await create_candidat()
        resp = await client.get("/analytics/overview", headers=cand["headers"])
        assert resp.status_code == 403
