"""Tests for the immigration deadline engine (Lot 3)."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.alert import AlertType
from app.models.candidate import Candidate
from app.models.deadline import Deadline, DeadlineType
from app.models.dossier import Dossier, DossierStatus
from app.models.program import ImmigrationProgram, Program
from app.models.user import Base, User, UserRole
from app.services.alert_service import AlertService

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
            email="admin@deadlines.com",
            hashed_password=hash_password("pass"),
            full_name="Admin",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return {"headers": _auth(admin), "user_id": admin.id}


async def create_candidat() -> dict:
    async with TestSessionLocal() as session:
        u = User(
            email="c@deadlines.com",
            hashed_password=hash_password("pass"),
            full_name="Cand",
            role=UserRole.candidat,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return {"headers": _auth(u)}


async def make_dossier(status=DossierStatus.en_cours) -> int:
    async with TestSessionLocal() as session:
        candidate = Candidate(
            first_name="Ada", last_name="Lovelace", email="ada@deadlines.com"
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="EE FSW",
            category="express_entry",
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=status,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)
        return dossier.id


async def add_deadline(
    dossier_id: int, dtype: DeadlineType, due_in_days: int, completed: bool = False
) -> int:
    async with TestSessionLocal() as session:
        dl = Deadline(
            dossier_id=dossier_id,
            deadline_type=dtype,
            due_date=datetime.now(timezone.utc) + timedelta(days=due_in_days),
            is_completed=completed,
        )
        session.add(dl)
        await session.commit()
        await session.refresh(dl)
        return dl.id


async def _get_dossier(dossier_id: int) -> Dossier:
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(Dossier).where(Dossier.id == dossier_id)
        )
        return result.scalar_one()


# =============================================================================
# Service unit tests
# =============================================================================


class TestDeadlineScan:
    async def test_ita_within_window_alerts(self):
        dossier_id = await make_dossier()
        await add_deadline(dossier_id, DeadlineType.ita_response, due_in_days=40)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert any(a.alert_type == AlertType.ita_response for a in alerts)

    async def test_ita_far_out_no_alert(self):
        dossier_id = await make_dossier()
        # 70 days out is beyond the 60-day ITA window
        await add_deadline(dossier_id, DeadlineType.ita_response, due_in_days=70)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
        assert not any(a.alert_type == AlertType.ita_response for a in alerts)

    async def test_biometrics_near_is_critical(self):
        dossier_id = await make_dossier()
        await add_deadline(dossier_id, DeadlineType.biometrics, due_in_days=3)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        bio = [a for a in alerts if a.alert_type == AlertType.biometrics]
        assert len(bio) == 1
        assert bio[0].severity.value == "critical"

    async def test_overdue_is_critical(self):
        dossier_id = await make_dossier()
        await add_deadline(dossier_id, DeadlineType.ppr, due_in_days=-2)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        ppr = [a for a in alerts if a.alert_type == AlertType.ppr]
        assert len(ppr) == 1
        assert ppr[0].severity.value == "critical"

    async def test_completed_deadline_skipped(self):
        dossier_id = await make_dossier()
        await add_deadline(
            dossier_id, DeadlineType.biometrics, due_in_days=5, completed=True
        )
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
        assert not any(a.alert_type == AlertType.biometrics for a in alerts)

    async def test_dedup_no_duplicate(self):
        dossier_id = await make_dossier()
        await add_deadline(dossier_id, DeadlineType.ita_response, due_in_days=20)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            first = await svc.scan_deadlines(session, dossier, None)
            await session.commit()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            second = await svc.scan_deadlines(session, dossier, None)
            await session.commit()
        assert len(first) == 1
        assert len(second) == 0

    async def test_permit_expiry_window(self):
        dossier_id = await make_dossier()
        await add_deadline(
            dossier_id, DeadlineType.work_permit_expiry, due_in_days=80
        )
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert any(a.alert_type == AlertType.permit_expiring for a in alerts)


# =============================================================================
# API integration tests
# =============================================================================


class TestDeadlinesAPI:
    async def test_create_and_list(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        due = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        resp = await client.post(
            "/deadlines",
            headers=admin["headers"],
            json={
                "dossier_id": dossier_id,
                "deadline_type": "ita_response",
                "due_date": due,
                "description": "ITA recue",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["deadline_type"] == "ita_response"
        assert resp.json()["source"] == "manual"

        listing = await client.get(
            f"/deadlines?dossier_id={dossier_id}", headers=admin["headers"]
        )
        assert listing.status_code == 200
        assert len(listing.json()) == 1

    async def test_create_unknown_dossier(self, client):
        admin = await create_admin()
        due = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        resp = await client.post(
            "/deadlines",
            headers=admin["headers"],
            json={"dossier_id": 9999, "deadline_type": "biometrics", "due_date": due},
        )
        assert resp.status_code == 404

    async def test_complete_hides_from_default_list(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        dl_id = await add_deadline(dossier_id, DeadlineType.ppr, due_in_days=15)

        resp = await client.post(
            f"/deadlines/{dl_id}/complete", headers=admin["headers"]
        )
        assert resp.status_code == 200

        listing = await client.get("/deadlines", headers=admin["headers"])
        assert all(d["id"] != dl_id for d in listing.json())

        with_completed = await client.get(
            "/deadlines?include_completed=true", headers=admin["headers"]
        )
        assert any(d["id"] == dl_id for d in with_completed.json())

    async def test_update_reschedule(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        dl_id = await add_deadline(dossier_id, DeadlineType.biometrics, due_in_days=10)
        new_due = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()

        resp = await client.put(
            f"/deadlines/{dl_id}",
            headers=admin["headers"],
            json={"due_date": new_due, "description": "reporte"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "reporte"

    async def test_delete(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        dl_id = await add_deadline(dossier_id, DeadlineType.custom, due_in_days=10)

        resp = await client.delete(
            f"/deadlines/{dl_id}", headers=admin["headers"]
        )
        assert resp.status_code == 204
        listing = await client.get("/deadlines", headers=admin["headers"])
        assert all(d["id"] != dl_id for d in listing.json())

    async def test_scan_generates_deadline_alerts(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        await add_deadline(dossier_id, DeadlineType.ita_response, due_in_days=25)

        scan = await client.post("/alerts/scan", headers=admin["headers"])
        assert scan.status_code == 200
        assert scan.json()["new_alerts"] >= 1

        listing = await client.get("/alerts", headers=admin["headers"])
        assert any(a["alert_type"] == "ita_response" for a in listing.json())

    async def test_rbac_candidat_forbidden(self, client):
        cand = await create_candidat()
        resp = await client.get("/deadlines", headers=cand["headers"])
        assert resp.status_code == 403
