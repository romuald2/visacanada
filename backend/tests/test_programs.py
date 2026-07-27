"""Tests for programs and requirements API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Base, User, UserRole
from app.models.program import Program, ImmigrationProgram
from app.models.program_requirement import ProgramRequirement, RequirementPriority
from app.seeds.seed_programs import seed_programs
from app.seeds.seed_requirements import seed_requirements

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
    """Create tables before each test and drop after."""
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
            full_name="Admin User",
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": "admin"})
        return user, {"Authorization": f"Bearer {token}"}


async def create_consultant() -> tuple[User, dict]:
    async with TestSessionLocal() as session:
        user = User(
            email="consultant@test.com",
            hashed_password=hash_password("password123"),
            full_name="Consultant User",
            role=UserRole.consultant,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(
            {"sub": str(user.id), "email": user.email, "role": "consultant"}
        )
        return user, {"Authorization": f"Bearer {token}"}


async def create_candidat() -> tuple[User, dict]:
    async with TestSessionLocal() as session:
        user = User(
            email="candidat@test.com",
            hashed_password=hash_password("password123"),
            full_name="Candidat User",
            role=UserRole.candidat,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(
            {"sub": str(user.id), "email": user.email, "role": "candidat"}
        )
        return user, {"Authorization": f"Bearer {token}"}


async def seed_test_programs():
    async with TestSessionLocal() as session:
        await seed_programs(session)


async def get_first_program_id() -> int:
    async with TestSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Program).limit(1))
        program = result.scalar_one()
        return program.id


# --- Programs List API Tests ---


class TestProgramsListAPI:
    async def test_list_programs(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()

        response = await client.get("/programs/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 16

    async def test_list_programs_filter_by_category(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()

        response = await client.get(
            "/programs/?category=Express Entry", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        for p in data:
            assert p["category"] == "Express Entry"

    async def test_list_programs_accessible_by_candidat(self, client: AsyncClient):
        _, headers = await create_candidat()
        await seed_test_programs()

        response = await client.get("/programs/", headers=headers)

        assert response.status_code == 200
        assert len(response.json()) == 16

    async def test_get_program(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        response = await client.get(f"/programs/{program_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == program_id
        assert data["name"] is not None

    async def test_get_program_not_found(self, client: AsyncClient):
        _, headers = await create_admin()

        response = await client.get("/programs/999", headers=headers)

        assert response.status_code == 404


# --- Requirements API Tests ---


class TestRequirementsAPI:
    async def test_get_requirements_empty(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        response = await client.get(
            f"/programs/{program_id}/requirements", headers=headers
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_create_requirement(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        response = await client.post(
            f"/programs/{program_id}/requirements",
            json={
                "program_id": program_id,
                "document_type": "identity",
                "document_name": "Passeport valide",
                "description": "Copie de toutes les pages",
                "priority": "mandatory",
                "imm_form_reference": "IMM 5690",
                "sort_order": 1,
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["document_name"] == "Passeport valide"
        assert data["priority"] == "mandatory"
        assert data["imm_form_reference"] == "IMM 5690"

    async def test_create_requirement_forbidden_for_consultant(self, client: AsyncClient):
        _, headers = await create_consultant()
        await seed_test_programs()
        program_id = await get_first_program_id()

        response = await client.post(
            f"/programs/{program_id}/requirements",
            json={
                "program_id": program_id,
                "document_type": "identity",
                "document_name": "Test",
            },
            headers=headers,
        )

        assert response.status_code == 403

    async def test_get_requirements_after_creation(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        # Create 2 requirements
        for i, name in enumerate(["Passeport", "Test de langue"], 1):
            await client.post(
                f"/programs/{program_id}/requirements",
                json={
                    "program_id": program_id,
                    "document_type": "identity",
                    "document_name": name,
                    "sort_order": i,
                },
                headers=headers,
            )

        response = await client.get(
            f"/programs/{program_id}/requirements", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_update_requirement_with_versioning(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        # Create requirement
        create_resp = await client.post(
            f"/programs/{program_id}/requirements",
            json={
                "program_id": program_id,
                "document_type": "identity",
                "document_name": "Passeport",
                "priority": "mandatory",
                "sort_order": 1,
            },
            headers=headers,
        )
        req_id = create_resp.json()["id"]

        # Update it
        response = await client.put(
            f"/programs/requirements/{req_id}",
            json={
                "document_name": "Passeport valide (toutes pages)",
                "priority": "mandatory",
                "change_reason": "Clarification des exigences IRCC",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_name"] == "Passeport valide (toutes pages)"

    async def test_requirement_history(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        # Create and update requirement
        create_resp = await client.post(
            f"/programs/{program_id}/requirements",
            json={
                "program_id": program_id,
                "document_type": "language",
                "document_name": "IELTS",
                "sort_order": 1,
            },
            headers=headers,
        )
        req_id = create_resp.json()["id"]

        await client.put(
            f"/programs/requirements/{req_id}",
            json={
                "document_name": "IELTS ou TEF",
                "change_reason": "Ajout TEF comme alternative",
            },
            headers=headers,
        )

        # Check history
        response = await client.get(
            f"/programs/requirements/{req_id}/history", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should have creation + update entries
        assert len(data) >= 2

    async def test_delete_requirement(self, client: AsyncClient):
        _, headers = await create_admin()
        await seed_test_programs()
        program_id = await get_first_program_id()

        create_resp = await client.post(
            f"/programs/{program_id}/requirements",
            json={
                "program_id": program_id,
                "document_type": "other",
                "document_name": "À supprimer",
                "sort_order": 99,
            },
            headers=headers,
        )
        req_id = create_resp.json()["id"]

        response = await client.delete(
            f"/programs/requirements/{req_id}", headers=headers
        )

        assert response.status_code == 204

    async def test_delete_requirement_not_found(self, client: AsyncClient):
        _, headers = await create_admin()

        response = await client.delete(
            "/programs/requirements/999", headers=headers
        )

        assert response.status_code == 404


# --- Seed Tests ---


class TestSeedRequirements:
    async def test_seed_requirements(self, client: AsyncClient):
        """Verify seed data loads correctly."""
        async with TestSessionLocal() as session:
            await seed_programs(session)
            created = await seed_requirements(session)

        assert created > 0

    async def test_seed_requirements_idempotent(self, client: AsyncClient):
        """Running seed twice doesn't create duplicates."""
        async with TestSessionLocal() as session:
            await seed_programs(session)
            await seed_requirements(session)
            created_second = await seed_requirements(session)

        assert created_second == 0
