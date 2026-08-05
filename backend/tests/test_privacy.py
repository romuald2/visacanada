"""Tests for privacy & PIPEDA compliance (consent, data rights, breaches)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.user import Base, User, UserRole
from app.services.privacy_service import PrivacyService

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


async def create_user(email: str, role: UserRole) -> dict:
    async with TestSessionLocal() as session:
        u = User(
            email=email,
            hashed_password=hash_password("pass"),
            full_name="User",
            role=role,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return {"headers": _auth(u), "id": u.id}


async def create_candidate_for(user_id: int) -> int:
    async with TestSessionLocal() as session:
        c = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@ex.com",
            passport_number="AB123456",
            nationality="Camerounaise",
            user_id=user_id,
        )
        session.add(c)
        await session.commit()
        await session.refresh(c)
        return c.id
# --- Unit tests: PrivacyService.assess_breach_notification ---


def test_breach_high_severity_requires_notification():
    svc = PrivacyService()
    assert svc.assess_breach_notification("high", 1, False) is True
    assert svc.assess_breach_notification("critical", 0, False) is True


def test_breach_sensitive_data_requires_notification():
    svc = PrivacyService()
    assert svc.assess_breach_notification("low", 1, True) is True


def test_breach_large_blast_radius_requires_notification():
    svc = PrivacyService()
    assert svc.assess_breach_notification("low", 100, False) is True


async def test_service_export_and_erase_directly():
    """Exercise the service methods directly against a session."""
    user_info = await create_user("svc@p.com", UserRole.candidat)
    await create_candidate_for(user_info["id"])

    async with TestSessionLocal() as session:
        u = await session.get(User, user_info["id"])

        export = await PrivacyService().export_user_data(u, session)
        assert export["user"]["email"] == "svc@p.com"
        assert len(export["candidates"]) == 1
        assert export["candidates"][0]["first_name"] == "Jean"

        result = await PrivacyService().erase_user_data(u, session)
        assert result["candidates_anonymized"] == 1

    # Verify anonymization persisted.
    async with TestSessionLocal() as session:
        from sqlalchemy import select as _select

        from app.models.candidate import Candidate

        rows = (await session.execute(_select(Candidate))).scalars().all()
        assert rows[0].first_name == "SUPPRIME"
        assert rows[0].passport_number is None
        assert rows[0].user_id is None


def test_breach_minor_no_notification():
    svc = PrivacyService()
    assert svc.assess_breach_notification("low", 5, False) is False
    assert svc.assess_breach_notification("medium", 10, False) is False


# --- API: policy ---


async def test_get_policy(client):
    user = await create_user("u@p.com", UserRole.candidat)
    resp = await client.get("/privacy/policy", headers=user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["policy_version"]
    assert any(c["type"] == "data_processing" for c in data["consent_types"])


# --- API: consent ---


async def test_record_and_list_consent(client):
    user = await create_user("u@p.com", UserRole.candidat)
    resp = await client.post(
        "/privacy/consent",
        headers=user["headers"],
        json={"consent_type": "data_processing", "granted": True},
    )
    assert resp.status_code == 201
    assert resp.json()["granted"] is True

    resp = await client.get("/privacy/consent", headers=user["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["granted"] is True


async def test_consent_revoke_updates_same_record(client):
    user = await create_user("u@p.com", UserRole.candidat)
    await client.post(
        "/privacy/consent",
        headers=user["headers"],
        json={"consent_type": "marketing", "granted": True},
    )
    resp = await client.post(
        "/privacy/consent",
        headers=user["headers"],
        json={"consent_type": "marketing", "granted": False},
    )
    assert resp.status_code == 201
    assert resp.json()["granted"] is False

    listing = await client.get("/privacy/consent", headers=user["headers"])
    assert len(listing.json()) == 1
    rec = listing.json()[0]
    assert rec["granted"] is False
    assert rec["revoked_at"] is not None


async def test_consent_invalid_type(client):
    user = await create_user("u@p.com", UserRole.candidat)
    resp = await client.post(
        "/privacy/consent",
        headers=user["headers"],
        json={"consent_type": "nonexistent", "granted": True},
    )
    assert resp.status_code == 400


# --- API: data-subject rights ---


async def test_export_my_data(client):
    user = await create_user("owner@p.com", UserRole.candidat)
    await create_candidate_for(user["id"])
    await client.post(
        "/privacy/consent",
        headers=user["headers"],
        json={"consent_type": "data_processing", "granted": True},
    )
    resp = await client.get("/privacy/my-data", headers=user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "owner@p.com"
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["passport_number"] == "AB123456"
    assert len(data["consents"]) == 1


async def test_erase_my_data_anonymizes(client):
    user = await create_user("owner@p.com", UserRole.candidat)
    await create_candidate_for(user["id"])
    await client.post(
        "/privacy/consent",
        headers=user["headers"],
        json={"consent_type": "data_processing", "granted": True},
    )
    resp = await client.delete("/privacy/my-data", headers=user["headers"])
    assert resp.status_code == 200
    assert resp.json()["candidates_anonymized"] == 1

    # After erasure, export shows anonymized candidate and no consents.
    export = await client.get("/privacy/my-data", headers=user["headers"])
    data = export.json()
    assert data["candidates"] == []  # user_id unlinked
    assert data["consents"] == []


# --- API: breach register (admin) ---


async def test_report_breach_requires_admin(client):
    consultant = await create_user("cons@p.com", UserRole.consultant)
    resp = await client.post(
        "/privacy/breaches",
        headers=consultant["headers"],
        json={"title": "X", "description": "Y", "severity": "high"},
    )
    assert resp.status_code == 403


async def test_report_breach_assesses_notification(client):
    admin = await create_user("admin@p.com", UserRole.admin)
    resp = await client.post(
        "/privacy/breaches",
        headers=admin["headers"],
        json={
            "title": "Fuite base de donnees",
            "description": "Acces non autorise",
            "severity": "critical",
            "affected_users_count": 50,
            "sensitive_data": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["requires_notification"] is True
    assert resp.json()["status"] == "open"


async def test_report_breach_invalid_severity(client):
    admin = await create_user("admin@p.com", UserRole.admin)
    resp = await client.post(
        "/privacy/breaches",
        headers=admin["headers"],
        json={"title": "X", "description": "Y", "severity": "apocalyptic"},
    )
    assert resp.status_code == 400


async def test_list_and_update_breach(client):
    admin = await create_user("admin@p.com", UserRole.admin)
    created = await client.post(
        "/privacy/breaches",
        headers=admin["headers"],
        json={"title": "Incident", "description": "desc", "severity": "medium"},
    )
    inc_id = created.json()["id"]

    listing = await client.get("/privacy/breaches", headers=admin["headers"])
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    resp = await client.put(
        f"/privacy/breaches/{inc_id}",
        headers=admin["headers"],
        json={"status": "resolved", "reported_to_authority": True, "users_notified": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["reported_to_authority"] is True
    assert data["users_notified"] is True
    assert data["resolved_at"] is not None


async def test_update_breach_not_found(client):
    admin = await create_user("admin@p.com", UserRole.admin)
    resp = await client.put(
        "/privacy/breaches/99999",
        headers=admin["headers"],
        json={"status": "resolved"},
    )
    assert resp.status_code == 404
