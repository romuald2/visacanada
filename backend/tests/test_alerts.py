"""Tests for the intelligent alert system."""

from datetime import datetime, timedelta, timezone

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.alert import Alert, AlertType
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus, DocumentType
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
            email="admin@alerts.com",
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
            email="c@alerts.com",
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
            first_name="Alan", last_name="Turing", email="alan@alerts.com"
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


async def add_document(dossier_id: int, doc_type: DocumentType, expires_in_days: int):
    async with TestSessionLocal() as session:
        doc = Document(
            dossier_id=dossier_id,
            document_type=doc_type,
            status=DocumentStatus.verified,
            file_name=f"{doc_type.value}.pdf",
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc.id


async def _get_dossier(dossier_id: int) -> Dossier:
    async with TestSessionLocal() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(Dossier).where(Dossier.id == dossier_id)
        )
        return result.scalar_one()


# =============================================================================
# Service unit tests
# =============================================================================


class TestAlertService:
    async def test_passport_expiring_within_6_months(self):
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=100)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.passport_expiring

    async def test_passport_not_expiring_no_alert(self):
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=400)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
        assert len(alerts) == 0

    async def test_expired_passport_is_critical(self):
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=-10)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert len(alerts) == 1
        assert alerts[0].severity.value == "critical"

    async def test_medical_expiring(self):
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.medical_exam, expires_in_days=30)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert any(a.alert_type == AlertType.medical_expiring for a in alerts)

    async def test_language_expiring(self):
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.language_test, expires_in_days=45)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert any(a.alert_type == AlertType.language_expiring for a in alerts)

    async def test_dedup_no_duplicate_on_rescan(self):
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=100)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            first = await svc.scan_dossier(session, dossier)
            await session.commit()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            second = await svc.scan_dossier(session, dossier)
            await session.commit()
        assert len(first) == 1
        assert len(second) == 0

    async def test_terminal_dossier_skipped(self):
        dossier_id = await make_dossier(status=DossierStatus.approuve)
        await add_document(dossier_id, DocumentType.passport, expires_in_days=10)
        svc = AlertService()
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(session, dossier)
        assert len(alerts) == 0

    async def test_express_entry_round_compatible(self):
        dossier_id = await make_dossier()
        svc = AlertService()
        latest = {"date": "2026-01-15", "score": 500}
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(
                session, dossier, candidate_crs=520, latest_round=latest
            )
            await session.commit()
        assert any(a.alert_type == AlertType.express_entry_round for a in alerts)

    async def test_express_entry_round_below_cutoff_no_alert(self):
        dossier_id = await make_dossier()
        svc = AlertService()
        latest = {"date": "2026-01-15", "score": 550}
        async with TestSessionLocal() as session:
            dossier = await _get_dossier(dossier_id)
            alerts = await svc.scan_dossier(
                session, dossier, candidate_crs=480, latest_round=latest
            )
        assert not any(
            a.alert_type == AlertType.express_entry_round for a in alerts
        )


# =============================================================================
# API integration tests
# =============================================================================


class TestAlertsAPI:
    async def test_scan_and_list(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=50)

        scan = await client.post("/alerts/scan", headers=admin["headers"])
        assert scan.status_code == 200
        assert scan.json()["new_alerts"] >= 1

        listing = await client.get("/alerts", headers=admin["headers"])
        assert listing.status_code == 200
        assert len(listing.json()) >= 1

    async def test_dismiss(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=50)
        await client.post("/alerts/scan", headers=admin["headers"])
        listing = await client.get("/alerts", headers=admin["headers"])
        alert_id = listing.json()[0]["id"]

        resp = await client.post(
            f"/alerts/{alert_id}/dismiss", headers=admin["headers"]
        )
        assert resp.status_code == 200
        after = await client.get("/alerts", headers=admin["headers"])
        assert all(a["id"] != alert_id for a in after.json())

    async def test_config_defaults(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        resp = await client.get(
            f"/alerts/config/{dossier_id}", headers=admin["headers"]
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is True
        assert resp.json()["channels"]["dashboard"] is True

    async def test_update_config_disables_type(self, client):
        admin = await create_admin()
        dossier_id = await make_dossier()
        await add_document(dossier_id, DocumentType.passport, expires_in_days=50)

        upd = await client.put(
            f"/alerts/config/{dossier_id}",
            headers=admin["headers"],
            json={"enabled_types": {"passport_expiring": False}},
        )
        assert upd.status_code == 200

        scan = await client.post("/alerts/scan", headers=admin["headers"])
        assert scan.json()["new_alerts"] == 0

    async def test_config_unknown_dossier(self, client):
        admin = await create_admin()
        resp = await client.put(
            "/alerts/config/9999",
            headers=admin["headers"],
            json={"is_enabled": False},
        )
        assert resp.status_code == 404

    async def test_rbac_candidat_forbidden(self, client):
        cand = await create_candidat()
        resp = await client.get("/alerts", headers=cand["headers"])
        assert resp.status_code == 403
