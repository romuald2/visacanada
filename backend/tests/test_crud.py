"""Tests for CRUD API endpoints: candidates, dossiers, documents."""

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


# PLACEHOLDER_HELPERS


async def create_test_user(role: UserRole = UserRole.admin) -> tuple[User, dict]:
    """Create a test user and return (user, auth_headers)."""
    async with TestSessionLocal() as session:
        user = User(
            email=f"{role.value}@test.com",
            hashed_password=hash_password("password123"),
            full_name=f"Test {role.value.title()}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        token = create_access_token(token_data)
        headers = {"Authorization": f"Bearer {token}"}
        return user, headers


async def create_test_program() -> Program:
    """Create a test program."""
    async with TestSessionLocal() as session:
        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="Federal Skilled Worker",
            category="Express Entry",
            is_active=True,
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)
        return program


async def create_test_candidate(user_id: int | None = None) -> Candidate:
    """Create a test candidate."""
    async with TestSessionLocal() as session:
        candidate = Candidate(
            user_id=user_id,
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@test.com",
            nationality="Française",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)
        return candidate


# --- Candidates API Tests ---


class TestCandidatesAPI:
    async def test_create_candidate(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)

        response = await client.post(
            "/candidates/",
            json={
                "first_name": "Marie",
                "last_name": "Tremblay",
                "email": "marie@test.com",
                "phone": "+15141234567",
                "nationality": "Canadienne",
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Marie"
        assert data["last_name"] == "Tremblay"
        assert data["email"] == "marie@test.com"
        assert data["id"] is not None

    async def test_create_candidate_duplicate_email(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        await create_test_candidate()

        response = await client.post(
            "/candidates/",
            json={
                "first_name": "Autre",
                "last_name": "Personne",
                "email": "jean.dupont@test.com",
            },
            headers=headers,
        )

        assert response.status_code == 409

    async def test_create_candidate_forbidden_for_candidat(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.candidat)

        response = await client.post(
            "/candidates/",
            json={
                "first_name": "Test",
                "last_name": "Forbidden",
                "email": "forbidden@test.com",
            },
            headers=headers,
        )

        assert response.status_code == 403

    async def test_list_candidates(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.consultant)
        await create_test_candidate()

        response = await client.get("/candidates/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["page"] == 1

    async def test_list_candidates_search(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        await create_test_candidate()

        response = await client.get(
            "/candidates/?search=Dupont", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_get_candidate(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()

        response = await client.get(
            f"/candidates/{candidate.id}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jean"

    async def test_get_candidate_not_found(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)

        response = await client.get("/candidates/999", headers=headers)

        assert response.status_code == 404

    async def test_update_candidate(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()

        response = await client.put(
            f"/candidates/{candidate.id}",
            json={"phone": "+33699999999", "current_city": "Lyon"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+33699999999"
        assert data["current_city"] == "Lyon"

    async def test_delete_candidate(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()

        response = await client.delete(
            f"/candidates/{candidate.id}", headers=headers
        )

        assert response.status_code == 204

    async def test_delete_candidate_forbidden_for_consultant(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.consultant)
        candidate = await create_test_candidate()

        response = await client.delete(
            f"/candidates/{candidate.id}", headers=headers
        )

        assert response.status_code == 403


# PLACEHOLDER_DOSSIERS_TESTS


class TestDossiersAPI:
    async def test_create_dossier(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        response = await client.post(
            "/dossiers/",
            json={
                "candidate_id": candidate.id,
                "program_id": program.id,
                "notes": "Dossier de test",
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["candidate_id"] == candidate.id
        assert data["program_id"] == program.id
        assert data["status"] == "nouveau"

    async def test_create_dossier_invalid_candidate(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        program = await create_test_program()

        response = await client.post(
            "/dossiers/",
            json={"candidate_id": 999, "program_id": program.id},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_create_dossier_invalid_program(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()

        response = await client.post(
            "/dossiers/",
            json={"candidate_id": candidate.id, "program_id": 999},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_list_dossiers(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        # Create a dossier
        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.nouveau,
            )
            session.add(dossier)
            await session.commit()

        response = await client.get("/dossiers/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "nouveau"

    async def test_list_dossiers_filter_by_status(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            d1 = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.nouveau,
            )
            d2 = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.soumis,
            )
            session.add_all([d1, d2])
            await session.commit()

        response = await client.get(
            "/dossiers/?status=soumis", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "soumis"

    async def test_get_dossier(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.en_cours,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            dossier_id = dossier.id

        response = await client.get(
            f"/dossiers/{dossier_id}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "en_cours"

    async def test_update_dossier_status(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.consultant)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.nouveau,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            dossier_id = dossier.id

        response = await client.put(
            f"/dossiers/{dossier_id}",
            json={"status": "en_cours", "compliance_score": 65.0},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "en_cours"
        assert data["compliance_score"] == 65.0

    async def test_update_dossier_soumis_sets_timestamp(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.en_cours,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            dossier_id = dossier.id

        response = await client.put(
            f"/dossiers/{dossier_id}",
            json={"status": "soumis"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["submitted_at"] is not None

    async def test_delete_dossier(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.nouveau,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            dossier_id = dossier.id

        response = await client.delete(
            f"/dossiers/{dossier_id}", headers=headers
        )

        assert response.status_code == 204

    async def test_delete_dossier_forbidden_for_consultant(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.consultant)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.nouveau,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            dossier_id = dossier.id

        response = await client.delete(
            f"/dossiers/{dossier_id}", headers=headers
        )

        assert response.status_code == 403


# PLACEHOLDER_DOCUMENTS_TESTS


class TestDocumentsAPI:
    async def _setup_dossier(self) -> tuple[int, dict]:
        """Helper: create user, candidate, program, dossier. Return (dossier_id, headers)."""
        _, headers = await create_test_user(UserRole.admin)
        candidate = await create_test_candidate()
        program = await create_test_program()

        async with TestSessionLocal() as session:
            dossier = Dossier(
                candidate_id=candidate.id,
                program_id=program.id,
                status=DossierStatus.en_cours,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            return dossier.id, headers

    async def test_create_document(self, client: AsyncClient):
        dossier_id, headers = await self._setup_dossier()

        response = await client.post(
            "/documents/",
            json={
                "dossier_id": dossier_id,
                "document_type": "passport",
                "file_name": "passport_scan.pdf",
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["document_type"] == "passport"
        assert data["status"] == "pending"
        assert data["file_name"] == "passport_scan.pdf"

    async def test_create_document_invalid_dossier(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)

        response = await client.post(
            "/documents/",
            json={
                "dossier_id": 999,
                "document_type": "passport",
                "file_name": "test.pdf",
            },
            headers=headers,
        )

        assert response.status_code == 404

    async def test_list_documents(self, client: AsyncClient):
        dossier_id, headers = await self._setup_dossier()

        # Create documents
        async with TestSessionLocal() as session:
            doc1 = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.passport,
                status=DocumentStatus.verified,
                file_name="passport.pdf",
            )
            doc2 = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.bank_statement,
                status=DocumentStatus.pending,
                file_name="bank.pdf",
            )
            session.add_all([doc1, doc2])
            await session.commit()

        response = await client.get(
            f"/documents/?dossier_id={dossier_id}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_documents_filter_status(self, client: AsyncClient):
        dossier_id, headers = await self._setup_dossier()

        async with TestSessionLocal() as session:
            doc1 = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.passport,
                status=DocumentStatus.verified,
                file_name="passport.pdf",
            )
            doc2 = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.bank_statement,
                status=DocumentStatus.pending,
                file_name="bank.pdf",
            )
            session.add_all([doc1, doc2])
            await session.commit()

        response = await client.get(
            f"/documents/?dossier_id={dossier_id}&status=verified",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "verified"

    async def test_get_document(self, client: AsyncClient):
        dossier_id, headers = await self._setup_dossier()

        async with TestSessionLocal() as session:
            doc = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.language_test,
                status=DocumentStatus.uploaded,
                file_name="ielts_results.pdf",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        response = await client.get(
            f"/documents/{doc_id}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "language_test"
        assert data["file_name"] == "ielts_results.pdf"

    async def test_get_document_not_found(self, client: AsyncClient):
        _, headers = await create_test_user(UserRole.admin)

        response = await client.get("/documents/999", headers=headers)

        assert response.status_code == 404

    async def test_update_document(self, client: AsyncClient):
        dossier_id, headers = await self._setup_dossier()

        async with TestSessionLocal() as session:
            doc = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.passport,
                status=DocumentStatus.uploaded,
                file_name="passport.pdf",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        response = await client.put(
            f"/documents/{doc_id}",
            json={
                "status": "verified",
                "compliance_score": 92.5,
                "ai_analysis": '{"valid": true}',
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["compliance_score"] == 92.5

    async def test_delete_document(self, client: AsyncClient):
        dossier_id, headers = await self._setup_dossier()

        async with TestSessionLocal() as session:
            doc = Document(
                dossier_id=dossier_id,
                document_type=DocumentType.photo,
                status=DocumentStatus.pending,
                file_name="photo.jpg",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        response = await client.delete(
            f"/documents/{doc_id}", headers=headers
        )

        assert response.status_code == 204

    async def test_create_document_forbidden_for_wrong_candidat(self, client: AsyncClient):
        """A candidat cannot add documents to someone else's dossier."""
        # Create admin and setup dossier for another candidate
        async with TestSessionLocal() as session:
            program = Program(
                code=ImmigrationProgram.visitor_visa,
                name="Visitor",
                category="Temporaire",
                is_active=True,
            )
            other_candidate = Candidate(
                first_name="Other",
                last_name="Person",
                email="other@test.com",
            )
            session.add_all([program, other_candidate])
            await session.commit()
            await session.refresh(program)
            await session.refresh(other_candidate)

            dossier = Dossier(
                candidate_id=other_candidate.id,
                program_id=program.id,
                status=DossierStatus.nouveau,
            )
            session.add(dossier)
            await session.commit()
            await session.refresh(dossier)
            dossier_id = dossier.id

        # Create candidat user (not linked to that candidate)
        _, headers = await create_test_user(UserRole.candidat)

        response = await client.post(
            "/documents/",
            json={
                "dossier_id": dossier_id,
                "document_type": "passport",
                "file_name": "hack.pdf",
            },
            headers=headers,
        )

        assert response.status_code == 403
