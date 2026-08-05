"""Tests for IRCC monitoring: feed parser, API, categorization."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.ircc_update import IRCCUpdate, IRCCUpdateCategory, IRCCUpdateSource
from app.models.user import Base, User, UserRole
from app.services.ircc_monitor import (
    IRCCFeedParser,
    categorize_update,
    generate_external_id,
)
from app.tasks.ircc_tasks import _notify_admins, _store_new_updates

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


async def create_admin() -> tuple[User, dict]:
    async with TestSessionLocal() as session:
        user = User(
            email="admin@test.com",
            hashed_password=hash_password("password123"),
            full_name="Admin",
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": "admin"})
        return user, {"Authorization": f"Bearer {token}"}


async def create_candidat() -> tuple[User, dict]:
    async with TestSessionLocal() as session:
        user = User(
            email="candidat@test.com",
            hashed_password=hash_password("password123"),
            full_name="Candidat",
            role=UserRole.candidat,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": "candidat"})
        return user, {"Authorization": f"Bearer {token}"}


SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>IRCC News</title>
  <entry>
    <title>New processing time standards for Express Entry</title>
    <link href="https://www.canada.ca/en/ircc/news/2026/01/processing-times.html"/>
    <summary>IRCC announces updated processing time standards for Express Entry applications.</summary>
    <published>2026-07-20T10:00:00Z</published>
  </entry>
  <entry>
    <title>New pilot program for healthcare workers</title>
    <link href="https://www.canada.ca/en/ircc/news/2026/01/healthcare-pilot.html"/>
    <summary>Canada launches a new pathway for international healthcare professionals.</summary>
    <published>2026-07-18T14:00:00Z</published>
  </entry>
  <entry>
    <title>Fee increase for temporary residence applications</title>
    <link href="https://www.canada.ca/en/ircc/news/2026/01/fees.html"/>
    <summary>Government announces fee changes effective September 2026.</summary>
    <published>2026-07-15T09:00:00Z</published>
  </entry>
</feed>"""


# --- Categorization Tests ---


class TestCategorization:
    def test_categorize_processing_time(self):
        result = categorize_update("New processing time standards announced")
        assert result == IRCCUpdateCategory.processing_time

    def test_categorize_new_program(self):
        result = categorize_update("Canada launches new pilot program for nurses")
        assert result == IRCCUpdateCategory.new_program

    def test_categorize_fee_change(self):
        result = categorize_update("Fee increase for work permits")
        assert result == IRCCUpdateCategory.fee_change

    def test_categorize_criteria_change(self):
        result = categorize_update("CRS minimum score changes for Express Entry")
        assert result == IRCCUpdateCategory.criteria_change

    def test_categorize_policy_update(self):
        result = categorize_update("Minister announces new immigration policy")
        assert result == IRCCUpdateCategory.policy_update

    def test_categorize_form_update(self):
        result = categorize_update("IMM 5690 form update released")
        assert result == IRCCUpdateCategory.form_update

    def test_categorize_general(self):
        result = categorize_update("Canada celebrates diversity week")
        assert result == IRCCUpdateCategory.general_news

    def test_generate_external_id_deterministic(self):
        id1 = generate_external_id("http://example.com", "Title")
        id2 = generate_external_id("http://example.com", "Title")
        assert id1 == id2
        assert len(id1) == 32

    def test_generate_external_id_unique(self):
        id1 = generate_external_id("http://a.com", "Title A")
        id2 = generate_external_id("http://b.com", "Title B")
        assert id1 != id2


# --- Feed Parser Tests ---


class TestIRCCFeedParser:
    def test_parse_atom_xml(self):
        parser = IRCCFeedParser()
        updates = parser._parse_atom_xml(SAMPLE_ATOM_FEED, "https://test.com")

        assert len(updates) == 3
        assert updates[0]["title"] == "New processing time standards for Express Entry"
        assert updates[0]["category"] == IRCCUpdateCategory.processing_time
        assert updates[1]["category"] == IRCCUpdateCategory.new_program
        assert updates[2]["category"] == IRCCUpdateCategory.fee_change

    def test_parse_atom_xml_invalid(self):
        parser = IRCCFeedParser()
        updates = parser._parse_atom_xml("not xml at all", "https://test.com")
        assert updates == []

    def test_parse_atom_xml_empty(self):
        parser = IRCCFeedParser()
        xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        updates = parser._parse_atom_xml(xml, "https://test.com")
        assert updates == []

    def test_parse_atom_xml_has_external_ids(self):
        parser = IRCCFeedParser()
        updates = parser._parse_atom_xml(SAMPLE_ATOM_FEED, "https://test.com")
        ids = [u["external_id"] for u in updates]
        # All unique
        assert len(set(ids)) == 3


# --- Store Updates Tests ---


class TestStoreUpdates:
    async def test_store_new_updates(self):
        parser = IRCCFeedParser()
        updates = parser._parse_atom_xml(SAMPLE_ATOM_FEED, "https://test.com")

        async with TestSessionLocal() as session:
            new = await _store_new_updates(session, updates)
            await session.commit()
            assert len(new) == 3

    async def test_store_updates_deduplication(self):
        parser = IRCCFeedParser()
        updates = parser._parse_atom_xml(SAMPLE_ATOM_FEED, "https://test.com")

        async with TestSessionLocal() as session:
            await _store_new_updates(session, updates)
            await session.commit()

        # Second run should not add duplicates
        async with TestSessionLocal() as session:
            new = await _store_new_updates(session, updates)
            await session.commit()
            assert len(new) == 0

    async def test_notify_admins(self):
        # Create admin
        async with TestSessionLocal() as session:
            admin = User(
                email="notif_admin@test.com",
                hashed_password=hash_password("pass"),
                full_name="Admin Notif",
                role=UserRole.admin,
            )
            session.add(admin)
            await session.commit()

        # Store updates and notify
        parser = IRCCFeedParser()
        updates = parser._parse_atom_xml(SAMPLE_ATOM_FEED, "https://test.com")

        async with TestSessionLocal() as session:
            new_updates = await _store_new_updates(session, updates)
            notified = await _notify_admins(session, new_updates)
            await session.commit()

            assert notified == 1


# --- API Tests ---


class TestIRCCAPI:
    async def test_list_updates_empty(self, client: AsyncClient):
        _, headers = await create_admin()

        response = await client.get("/ircc/updates", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_updates_with_data(self, client: AsyncClient):
        _, headers = await create_admin()

        # Insert test data
        async with TestSessionLocal() as session:
            update = IRCCUpdate(
                title="Test IRCC Update",
                category=IRCCUpdateCategory.policy_update,
                source=IRCCUpdateSource.atom_feed,
                external_id="test123",
            )
            session.add(update)
            await session.commit()

        response = await client.get("/ircc/updates", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Test IRCC Update"

    async def test_list_updates_filter_category(self, client: AsyncClient):
        _, headers = await create_admin()

        async with TestSessionLocal() as session:
            u1 = IRCCUpdate(
                title="Processing time update",
                category=IRCCUpdateCategory.processing_time,
                source=IRCCUpdateSource.atom_feed,
                external_id="pt1",
            )
            u2 = IRCCUpdate(
                title="New program",
                category=IRCCUpdateCategory.new_program,
                source=IRCCUpdateSource.atom_feed,
                external_id="np1",
            )
            session.add_all([u1, u2])
            await session.commit()

        response = await client.get("/ircc/updates?category=processing_time", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "processing_time"

    async def test_get_update_marks_as_read(self, client: AsyncClient):
        _, headers = await create_admin()

        async with TestSessionLocal() as session:
            update = IRCCUpdate(
                title="Unread update",
                category=IRCCUpdateCategory.general_news,
                source=IRCCUpdateSource.atom_feed,
                external_id="unread1",
                is_read=False,
            )
            session.add(update)
            await session.commit()
            await session.refresh(update)
            update_id = update.id

        response = await client.get(f"/ircc/updates/{update_id}", headers=headers)

        assert response.status_code == 200
        assert response.json()["is_read"] is True

    async def test_get_update_not_found(self, client: AsyncClient):
        _, headers = await create_admin()

        response = await client.get("/ircc/updates/999", headers=headers)

        assert response.status_code == 404

    async def test_updates_forbidden_for_candidat(self, client: AsyncClient):
        _, headers = await create_candidat()

        response = await client.get("/ircc/updates", headers=headers)

        assert response.status_code == 403

    async def test_refresh_forbidden_for_non_admin(self, client: AsyncClient):
        async with TestSessionLocal() as session:
            user = User(
                email="cons@test.com",
                hashed_password=hash_password("pass"),
                full_name="Cons",
                role=UserRole.consultant,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            token = create_access_token(
                {"sub": str(user.id), "email": user.email, "role": "consultant"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.post("/ircc/updates/refresh", headers=headers)

        assert response.status_code == 403

    async def test_stats_endpoint(self, client: AsyncClient):
        _, headers = await create_admin()

        async with TestSessionLocal() as session:
            session.add(
                IRCCUpdate(
                    title="Stats test",
                    category=IRCCUpdateCategory.policy_update,
                    source=IRCCUpdateSource.atom_feed,
                    external_id="stats1",
                    is_read=False,
                )
            )
            await session.commit()

        response = await client.get("/ircc/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_updates"] == 1
        assert data["unread"] == 1
        assert "policy_update" in data["by_category"]
