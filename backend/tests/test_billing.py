"""Tests for billing (invoices, payments, reminders, dashboard)."""

from datetime import datetime, timedelta, timezone

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.user import Base, User, UserRole
from app.services.billing_service import BillingService

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
            email="admin@bill.com",
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
            email="c@bill.com",
            hashed_password=hash_password("pass"),
            full_name="Cand",
            role=UserRole.candidat,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return {"headers": _auth(u)}


async def make_candidate() -> int:
    async with TestSessionLocal() as session:
        c = Candidate(first_name="Jean", last_name="Client", email="jc@bill.com")
        session.add(c)
        await session.commit()
        await session.refresh(c)
        return c.id
# --- Unit tests: BillingService ---


def test_compute_totals_government_fee_not_taxed():
    svc = BillingService()
    items = [
        {"kind": "service_fee", "quantity": 1, "unit_price": 1000.0},
        {"kind": "government_fee", "quantity": 1, "unit_price": 850.0},
    ]
    totals = svc.compute_totals(items, tax_rate=0.15)
    assert totals["subtotal"] == 1850.0
    # tax only on the 1000 service fee
    assert totals["tax"] == 150.0
    assert totals["total"] == 2000.0


def test_compute_totals_quantity():
    svc = BillingService()
    items = [{"kind": "service_fee", "quantity": 3, "unit_price": 100.0}]
    totals = svc.compute_totals(items, tax_rate=0.10)
    assert totals["subtotal"] == 300.0
    assert totals["tax"] == 30.0
    assert totals["total"] == 330.0


def test_generate_invoice_number_format():
    svc = BillingService()
    num = svc.generate_invoice_number(123)
    assert num.startswith("INV-")
    assert num.endswith("-000123")


def test_apply_payment_status():
    svc = BillingService()
    assert svc.apply_payment_status(100.0, 0.0) == "sent"
    assert svc.apply_payment_status(100.0, 40.0) == "partially_paid"
    assert svc.apply_payment_status(100.0, 100.0) == "paid"
    assert svc.apply_payment_status(100.0, 120.0) == "paid"


async def test_create_payment_intent_mock():
    svc = BillingService()
    svc._stripe_key = ""  # force mock
    intent = await svc.create_payment_intent(150.0, "cad")
    assert intent["provider"] == "mock"
    assert intent["amount"] == 15000
    assert intent["currency"] == "cad"
    assert intent["id"].startswith("pi_mock_")


# --- API integration tests ---


async def test_create_invoice_computes_totals(client):
    admin = await create_admin()
    cid = await make_candidate()
    resp = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "service_fee", "description": "Consultation", "quantity": 1, "unit_price": 1000.0},
                {"kind": "government_fee", "description": "Frais IRCC", "quantity": 1, "unit_price": 850.0},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["subtotal"] == 1850.0
    assert data["tax"] == round(1000.0 * 0.14975, 2)
    assert data["status"] == "draft"
    assert data["invoice_number"].startswith("INV-")
    assert len(data["line_items"]) == 2
    assert data["balance"] == data["total"]


async def test_create_invoice_candidate_not_found(client):
    admin = await create_admin()
    resp = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": 99999,
            "line_items": [
                {"kind": "service_fee", "description": "X", "quantity": 1, "unit_price": 10.0}
            ],
        },
    )
    assert resp.status_code == 404


async def test_create_invoice_requires_line_items(client):
    admin = await create_admin()
    cid = await make_candidate()
    resp = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={"candidate_id": cid, "line_items": []},
    )
    assert resp.status_code == 400


async def test_list_and_filter_invoices(client):
    admin = await create_admin()
    cid = await make_candidate()
    await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "service_fee", "description": "A", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    resp = await client.get("/billing/invoices", headers=admin["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(
        f"/billing/invoices?candidate_id={cid}", headers=admin["headers"]
    )
    assert len(resp.json()) == 1

    resp = await client.get(
        "/billing/invoices?status=draft", headers=admin["headers"]
    )
    assert len(resp.json()) == 1

    resp = await client.get(
        "/billing/invoices?status=paid", headers=admin["headers"]
    )
    assert len(resp.json()) == 0


async def test_get_invoice(client):
    admin = await create_admin()
    cid = await make_candidate()
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "service_fee", "description": "A", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    inv_id = created.json()["id"]
    resp = await client.get(f"/billing/invoices/{inv_id}", headers=admin["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == inv_id

    resp = await client.get("/billing/invoices/99999", headers=admin["headers"])
    assert resp.status_code == 404


async def test_send_invoice(client):
    admin = await create_admin()
    cid = await make_candidate()
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "service_fee", "description": "A", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    inv_id = created.json()["id"]
    resp = await client.post(f"/billing/invoices/{inv_id}/send", headers=admin["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
async def test_payment_intent_mock(client):
    admin = await create_admin()
    cid = await make_candidate()
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "service_fee", "description": "A", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    inv_id = created.json()["id"]
    resp = await client.post(
        f"/billing/invoices/{inv_id}/payment-intent", headers=admin["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["amount"] > 0


async def test_record_payment_partial_then_full(client):
    admin = await create_admin()
    cid = await make_candidate()
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "government_fee", "description": "Frais", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    inv = created.json()
    inv_id = inv["id"]
    total = inv["total"]

    # partial
    resp = await client.post(
        f"/billing/invoices/{inv_id}/payments",
        headers=admin["headers"],
        json={"amount": 40.0, "method": "manual"},
    )
    assert resp.status_code == 201
    assert resp.json()["invoice_status"] == "partially_paid"
    assert resp.json()["balance"] == round(total - 40.0, 2)

    # full
    resp = await client.post(
        f"/billing/invoices/{inv_id}/payments",
        headers=admin["headers"],
        json={"amount": total - 40.0, "method": "manual"},
    )
    assert resp.status_code == 201
    assert resp.json()["invoice_status"] == "paid"
    assert resp.json()["balance"] == 0.0


async def test_record_payment_invalid_amount(client):
    admin = await create_admin()
    cid = await make_candidate()
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "service_fee", "description": "A", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    inv_id = created.json()["id"]
    resp = await client.post(
        f"/billing/invoices/{inv_id}/payments",
        headers=admin["headers"],
        json={"amount": 0, "method": "manual"},
    )
    assert resp.status_code == 400


async def test_reminders_marks_overdue(client):
    admin = await create_admin()
    cid = await make_candidate()
    past = (datetime.now(timezone.utc) - timedelta(days=5)).replace(tzinfo=None)
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "due_date": past.isoformat(),
            "line_items": [
                {"kind": "service_fee", "description": "A", "quantity": 1, "unit_price": 100.0}
            ],
        },
    )
    inv_id = created.json()["id"]
    await client.post(f"/billing/invoices/{inv_id}/send", headers=admin["headers"])

    resp = await client.get("/billing/reminders", headers=admin["headers"])
    assert resp.status_code == 200
    reminders = resp.json()
    assert len(reminders) == 1
    assert reminders[0]["is_overdue"] is True

    # invoice status now overdue
    resp = await client.get(f"/billing/invoices/{inv_id}", headers=admin["headers"])
    assert resp.json()["status"] == "overdue"


async def test_dashboard(client):
    admin = await create_admin()
    cid = await make_candidate()
    created = await client.post(
        "/billing/invoices",
        headers=admin["headers"],
        json={
            "candidate_id": cid,
            "line_items": [
                {"kind": "government_fee", "description": "Frais", "quantity": 1, "unit_price": 200.0}
            ],
        },
    )
    inv_id = created.json()["id"]
    await client.post(
        f"/billing/invoices/{inv_id}/payments",
        headers=admin["headers"],
        json={"amount": 50.0, "method": "manual"},
    )
    resp = await client.get("/billing/dashboard", headers=admin["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_invoiced"] == 200.0
    assert data["total_collected"] == 50.0
    assert data["outstanding"] == 150.0
    assert data["invoice_count"] == 1
    assert "stripe_enabled" in data


async def test_candidat_forbidden(client):
    cand = await create_candidat()
    resp = await client.get("/billing/invoices", headers=cand["headers"])
    assert resp.status_code == 403

    resp = await client.get("/billing/dashboard", headers=cand["headers"])
    assert resp.status_code == 403
