"""Tests for letter generation."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.user import Base, User, UserRole
from app.services.letter_generator import (
    LetterGenerator,
    LetterType,
    letter_generator,
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


async def create_admin() -> dict:
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@letters.com",
            hashed_password=hash_password("pass"),
            full_name="Admin Letters",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(
            {"sub": str(admin.id), "email": admin.email, "role": "admin"}
        )
        return {"headers": {"Authorization": f"Bearer {token}"}, "user_id": admin.id}


async def create_candidat_user() -> dict:
    async with TestSessionLocal() as session:
        user = User(
            email="cand@letters.com",
            hashed_password=hash_password("pass"),
            full_name="Cand User",
            role=UserRole.candidat,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(
            {"sub": str(user.id), "email": user.email, "role": "candidat"}
        )
        return {"headers": {"Authorization": f"Bearer {token}"}, "user_id": user.id}


async def create_candidate(user_id: int) -> int:
    async with TestSessionLocal() as session:
        candidate = Candidate(
            user_id=user_id,
            first_name="Marie",
            last_name="Curie",
            email="marie@letters.com",
            phone="+15140000000",
            nationality="FR",
            passport_number="AB123456",
            current_city="Montreal",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)
        return candidate.id


# =============================================================================
# Unit Tests - LetterGenerator service
# =============================================================================


class TestLetterGeneratorService:
    def test_get_available_templates(self):
        templates = letter_generator.get_available_templates()
        types = {t["type"] for t in templates}
        assert "motivation" in types
        assert "explanation" in types
        assert "financial_support" in types
        assert "cover_letter" in types
        for t in templates:
            assert t["title"]

    def test_template_generation_motivation(self):
        gen = LetterGenerator()
        gen._api_key = ""  # force template fallback
        content = gen._generate_from_template(
            LetterType.motivation,
            {"full_name": "Marie Curie", "nationality": "FR"},
        )
        assert "Marie Curie" in content
        assert "FR" in content
        assert "motivation" in content.lower()

    def test_template_missing_keys_use_placeholders(self):
        gen = LetterGenerator()
        content = gen._generate_from_template(LetterType.motivation, {})
        # Missing personalized fields fall back to bracketed placeholders
        assert "[" in content and "]" in content

    def test_template_unknown_type(self):
        gen = LetterGenerator()
        content = gen._generate_from_template("nonexistent", {})
        assert "non supporte" in content

    def test_ai_available_flag(self):
        gen = LetterGenerator()
        gen._api_key = ""
        assert gen.ai_available is False
        gen._api_key = "sk-test"
        assert gen.ai_available is True

    async def test_generate_falls_back_to_template(self):
        gen = LetterGenerator()
        gen._api_key = ""  # no AI
        result = await gen.generate(
            LetterType.motivation,
            {"full_name": "Marie Curie"},
            program="express_entry",
        )
        assert result["method"] == "template"
        assert "Marie Curie" in result["content"]
        assert result["program"] == "express_entry"

    def test_build_prompt_includes_program_context(self):
        gen = LetterGenerator()
        prompt = gen._build_prompt(
            LetterType.motivation,
            {"full_name": "Marie Curie"},
            "study_permit",
            "Insister sur le retour au pays",
        )
        assert "Marie Curie" in prompt
        assert "study_permit" in prompt
        assert "retour au pays" in prompt
        assert "francais" in prompt.lower()


# =============================================================================
# Integration Tests - Letters API
# =============================================================================


class TestLettersAPI:
    async def test_list_templates(self, client):
        auth = await create_admin()
        resp = await client.get("/letters/templates", headers=auth["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    async def test_generate_letter(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        resp = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={
                "candidate_id": cand_id,
                "letter_type": "motivation",
                "program": "express_entry",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"]
        assert "Marie Curie" in data["content"]
        assert data["generation_method"] in ("ai", "template")
        assert data["letter_type"] == "motivation"

    async def test_generate_letter_unknown_candidate(self, client):
        auth = await create_admin()
        resp = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={"candidate_id": 9999, "letter_type": "motivation"},
        )
        assert resp.status_code == 404

    async def test_generate_letter_invalid_type(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        resp = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={"candidate_id": cand_id, "letter_type": "bogus"},
        )
        assert resp.status_code == 400

    async def test_get_letter(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        gen = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={"candidate_id": cand_id, "letter_type": "explanation"},
        )
        letter_id = gen.json()["id"]
        resp = await client.get(f"/letters/{letter_id}", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["id"] == letter_id
        assert resp.json()["content"]

    async def test_get_letter_not_found(self, client):
        auth = await create_admin()
        resp = await client.get("/letters/9999", headers=auth["headers"])
        assert resp.status_code == 404

    async def test_update_letter(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        gen = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={"candidate_id": cand_id, "letter_type": "motivation"},
        )
        letter_id = gen.json()["id"]
        resp = await client.put(
            f"/letters/{letter_id}",
            headers=auth["headers"],
            json={"content": "Contenu modifie manuellement."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Contenu modifie manuellement."
        assert data["is_edited"] is True
        assert data["version"] == 2

    async def test_update_letter_not_found(self, client):
        auth = await create_admin()
        resp = await client.put(
            "/letters/9999",
            headers=auth["headers"],
            json={"content": "x"},
        )
        assert resp.status_code == 404

    async def test_list_candidate_letters(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        for lt in ("motivation", "explanation"):
            await client.post(
                "/letters/generate",
                headers=auth["headers"],
                json={"candidate_id": cand_id, "letter_type": lt},
            )
        resp = await client.get(
            f"/letters/candidate/{cand_id}", headers=auth["headers"]
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_export_pdf(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        gen = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={"candidate_id": cand_id, "letter_type": "motivation"},
        )
        letter_id = gen.json()["id"]
        resp = await client.get(
            f"/letters/{letter_id}/pdf", headers=auth["headers"]
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    async def test_delete_letter(self, client):
        auth = await create_admin()
        cand_id = await create_candidate(auth["user_id"])
        gen = await client.post(
            "/letters/generate",
            headers=auth["headers"],
            json={"candidate_id": cand_id, "letter_type": "motivation"},
        )
        letter_id = gen.json()["id"]
        resp = await client.delete(
            f"/letters/{letter_id}", headers=auth["headers"]
        )
        assert resp.status_code == 200
        # Confirm gone
        check = await client.get(f"/letters/{letter_id}", headers=auth["headers"])
        assert check.status_code == 404

    async def test_rbac_candidat_forbidden(self, client):
        auth = await create_candidat_user()
        resp = await client.get("/letters/templates", headers=auth["headers"])
        assert resp.status_code == 403

    async def test_requires_auth(self, client):
        resp = await client.get("/letters/templates")
        assert resp.status_code in (401, 403)
