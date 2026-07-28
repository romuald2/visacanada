"""Tests for family dossiers (multi-candidate groups)."""

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.dossier import Dossier, DossierStatus
from app.models.program import ImmigrationProgram, Program
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


async def create_admin() -> dict:
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@fam.com",
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
            email="c@fam.com",
            hashed_password=hash_password("pass"),
            full_name="Cand",
            role=UserRole.candidat,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return {"headers": _auth(u)}


async def make_candidate(first: str, email: str) -> int:
    async with TestSessionLocal() as session:
        c = Candidate(first_name=first, last_name="Test", email=email)
        session.add(c)
        await session.commit()
        await session.refresh(c)
        return c.id


async def make_dossier_with_doc(candidate_id: int) -> tuple[int, int]:
    async with TestSessionLocal() as session:
        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="EE",
            category="express_entry",
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate_id,
            program_id=program.id,
            status=DossierStatus.en_cours,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        doc = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.proof_of_funds,
            status=DocumentStatus.verified,
            file_name="funds.pdf",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return dossier.id, doc.id


async def _create_group(client, headers, principal_id, name="Famille Dupont"):
    resp = await client.post(
        "/family",
        headers=headers,
        json={"name": name, "principal_candidate_id": principal_id},
    )
    return resp


class TestFamilyGroups:
    async def test_create_group(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        resp = await _create_group(client, admin["headers"], principal)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Famille Dupont"

    async def test_create_group_unknown_candidate(self, client):
        admin = await create_admin()
        resp = await _create_group(client, admin["headers"], 9999)
        assert resp.status_code == 404

    async def test_principal_is_first_member(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]

        view = await client.get(f"/family/{gid}", headers=admin["headers"])
        members = view.json()["members"]
        assert len(members) == 1
        assert members[0]["role"] == "principal"
        assert members[0]["candidate_id"] == principal

    async def test_add_member(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        spouse = await make_candidate("Marie", "marie@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]

        resp = await client.post(
            f"/family/{gid}/members",
            headers=admin["headers"],
            json={"candidate_id": spouse, "role": "conjoint"},
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "conjoint"

    async def test_add_member_invalid_role(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        spouse = await make_candidate("Marie", "marie@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]
        resp = await client.post(
            f"/family/{gid}/members",
            headers=admin["headers"],
            json={"candidate_id": spouse, "role": "bogus"},
        )
        assert resp.status_code == 400

    async def test_add_duplicate_member(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]
        # principal already a member
        resp = await client.post(
            f"/family/{gid}/members",
            headers=admin["headers"],
            json={"candidate_id": principal, "role": "principal"},
        )
        assert resp.status_code == 409

    async def test_remove_member(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        child = await make_candidate("Paul", "paul@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]
        await client.post(
            f"/family/{gid}/members",
            headers=admin["headers"],
            json={"candidate_id": child, "role": "enfant"},
        )
        resp = await client.delete(
            f"/family/{gid}/members/{child}", headers=admin["headers"]
        )
        assert resp.status_code == 200

    async def test_cannot_remove_principal(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]
        resp = await client.delete(
            f"/family/{gid}/members/{principal}", headers=admin["headers"]
        )
        assert resp.status_code == 400

    async def test_list_families(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        await _create_group(client, admin["headers"], principal)
        resp = await client.get("/family", headers=admin["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["member_count"] == 1


class TestSharedDocuments:
    async def test_share_document(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        _, doc_id = await make_dossier_with_doc(principal)
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]

        resp = await client.post(
            f"/family/{gid}/shared-documents",
            headers=admin["headers"],
            json={"document_id": doc_id, "note": "Preuve de fonds commune"},
        )
        assert resp.status_code == 201

        view = await client.get(f"/family/{gid}", headers=admin["headers"])
        shared = view.json()["shared_documents"]
        assert len(shared) == 1
        assert shared[0]["document_id"] == doc_id
        assert shared[0]["file_name"] == "funds.pdf"

    async def test_share_unknown_document(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]
        resp = await client.post(
            f"/family/{gid}/shared-documents",
            headers=admin["headers"],
            json={"document_id": 9999},
        )
        assert resp.status_code == 404

    async def test_share_duplicate_document(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        _, doc_id = await make_dossier_with_doc(principal)
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]
        await client.post(
            f"/family/{gid}/shared-documents",
            headers=admin["headers"],
            json={"document_id": doc_id},
        )
        resp = await client.post(
            f"/family/{gid}/shared-documents",
            headers=admin["headers"],
            json={"document_id": doc_id},
        )
        assert resp.status_code == 409


class TestFamilyView:
    async def test_coordinated_view_shows_dossiers(self, client):
        admin = await create_admin()
        principal = await make_candidate("Jean", "jean@fam.com")
        await make_dossier_with_doc(principal)
        group = await _create_group(client, admin["headers"], principal)
        gid = group.json()["id"]

        view = await client.get(f"/family/{gid}", headers=admin["headers"])
        assert view.status_code == 200
        member = view.json()["members"][0]
        assert len(member["dossiers"]) == 1
        assert member["dossiers"][0]["status"] == "en_cours"

    async def test_view_unknown_group(self, client):
        admin = await create_admin()
        resp = await client.get("/family/9999", headers=admin["headers"])
        assert resp.status_code == 404

    async def test_rbac_candidat_forbidden(self, client):
        cand = await create_candidat()
        resp = await client.get("/family", headers=cand["headers"])
        assert resp.status_code == 403
