"""Tests for the knowledge base & RAG chatbot."""

import pytest

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Base, User, UserRole
from app.services.rag_service import RagService, cosine_similarity

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
# --- Unit tests: RagService ---


def test_chunk_text_splits_paragraphs():
    svc = RagService()
    text = "\n\n".join([f"Paragraphe numero {i} sur l'immigration canadienne." for i in range(30)])
    chunks = svc.chunk_text(text)
    assert len(chunks) >= 2
    assert all(c.strip() for c in chunks)


def test_chunk_text_empty():
    svc = RagService()
    assert svc.chunk_text("   ") == []


def test_local_embedding_deterministic():
    svc = RagService()
    a = svc._local_embedding("permis de travail")
    b = svc._local_embedding("permis de travail")
    assert a == b
    assert len(a) == svc._dim


def test_cosine_similarity_self_is_one():
    svc = RagService()
    v = svc._local_embedding("express entry crs pointage")
    assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_mismatched_len():
    assert cosine_similarity([1.0, 0.0], [1.0]) == 0.0


async def test_embed_batch_local_fallback():
    svc = RagService()
    svc._voyage_key = ""  # force local
    vecs = await svc.embed_batch(["texte un", "texte deux"])
    assert len(vecs) == 2
    assert len(vecs[0]) == svc._dim


def test_rank_chunks_orders_by_relevance():
    svc = RagService()
    svc._voyage_key = ""
    relevant = svc._local_embedding("delai de traitement du permis de travail")
    noise = svc._local_embedding("recette de cuisine tarte aux pommes")
    query_vec = svc._local_embedding("permis de travail delai")
    chunks = [
        {"content": "recette de cuisine tarte aux pommes", "embedding": noise, "document_id": 2, "title": "N"},
        {"content": "delai de traitement du permis de travail", "embedding": relevant, "document_id": 1, "title": "R"},
    ]
    ranked = svc.rank_chunks("permis de travail delai", query_vec, chunks, top_k=2)
    assert ranked[0]["document_id"] == 1
    assert ranked[0]["score"] >= ranked[1]["score"]


async def test_generate_answer_no_context():
    svc = RagService()
    result = await svc.generate_answer("question", [])
    assert result["method"] == "no_context"


async def test_generate_answer_extractive_fallback():
    svc = RagService()
    svc._anthropic_key = ""  # force extractive
    contexts = [{"title": "Doc", "content": "Le delai est de 6 mois pour Express Entry."}]
    result = await svc.generate_answer("Quel est le delai?", contexts)
    assert result["method"] == "extractive"
    assert "delai" in result["answer"].lower()


# --- API integration tests ---


async def test_ingest_document(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    resp = await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={
            "title": "Express Entry",
            "content": "Express Entry est un systeme de gestion des demandes. " * 40,
            "source_type": "ircc_page",
            "source_url": "https://ircc.example/ee",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["chunk_count"] >= 1
    assert data["reingested"] is False


async def test_ingest_unchanged_is_skipped(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    payload = {
        "title": "Doc",
        "content": "Contenu identique sur les procedures IRCC. " * 20,
        "source_url": "https://ircc.example/x",
    }
    first = await client.post("/knowledge/documents", headers=editor["headers"], json=payload)
    assert first.status_code == 201
    second = await client.post("/knowledge/documents", headers=editor["headers"], json=payload)
    assert second.status_code == 201
    assert second.json()["reingested"] is False
    assert second.json()["document_id"] == first.json()["document_id"]


async def test_reingest_on_content_change(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    url = "https://ircc.example/y"
    await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={"title": "V1", "content": "Ancien contenu. " * 20, "source_url": url},
    )
    resp = await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={"title": "V2", "content": "Nouveau contenu different. " * 20, "source_url": url},
    )
    assert resp.status_code == 201
    assert resp.json()["reingested"] is True


async def test_ingest_empty_content(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    resp = await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={"title": "X", "content": "   "},
    )
    assert resp.status_code == 400


async def test_ingest_requires_editor_role(client):
    candidat = await create_user("cand@kb.com", UserRole.candidat)
    resp = await client.post(
        "/knowledge/documents",
        headers=candidat["headers"],
        json={"title": "X", "content": "abc " * 20},
    )
    assert resp.status_code == 403


async def test_list_documents(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={"title": "Doc A", "content": "Contenu A. " * 20},
    )
    resp = await client.get("/knowledge/documents", headers=editor["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_delete_document(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    created = await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={"title": "Doc", "content": "Contenu. " * 20},
    )
    doc_id = created.json()["document_id"]
    resp = await client.delete(f"/knowledge/documents/{doc_id}", headers=editor["headers"])
    assert resp.status_code == 200
    resp = await client.delete("/knowledge/documents/99999", headers=editor["headers"])
    assert resp.status_code == 404


async def test_ask_creates_conversation_with_citations(client):
    editor = await create_user("editor@kb.com", UserRole.consultant)
    await client.post(
        "/knowledge/documents",
        headers=editor["headers"],
        json={
            "title": "Delais Express Entry",
            "content": (
                "Le delai de traitement d'une demande Express Entry est "
                "generalement de six mois apres la reception de la demande complete. "
            ) * 10,
            "source_url": "https://ircc.example/delais",
        },
    )
    resp = await client.post(
        "/knowledge/ask",
        headers=editor["headers"],
        json={"question": "Quel est le delai de traitement Express Entry?"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["conversation_id"] is not None
    assert data["answer"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["source_url"] == "https://ircc.example/delais"


async def test_ask_empty_question(client):
    user = await create_user("u@kb.com", UserRole.candidat)
    resp = await client.post(
        "/knowledge/ask", headers=user["headers"], json={"question": "  "}
    )
    assert resp.status_code == 400


async def test_ask_no_documents_returns_no_context(client):
    user = await create_user("u@kb.com", UserRole.candidat)
    resp = await client.post(
        "/knowledge/ask",
        headers=user["headers"],
        json={"question": "Question sans base de connaissances?"},
    )
    assert resp.status_code == 200
    assert resp.json()["method"] == "no_context"


async def test_conversation_history_and_isolation(client):
    user_a = await create_user("a@kb.com", UserRole.candidat)
    user_b = await create_user("b@kb.com", UserRole.candidat)
    ask = await client.post(
        "/knowledge/ask", headers=user_a["headers"], json={"question": "Bonjour?"}
    )
    conv_id = ask.json()["conversation_id"]

    # Owner sees full history (user + assistant messages).
    resp = await client.get(
        f"/knowledge/conversations/{conv_id}", headers=user_a["headers"]
    )
    assert resp.status_code == 200
    assert len(resp.json()["messages"]) == 2

    # Other user cannot access it.
    resp = await client.get(
        f"/knowledge/conversations/{conv_id}", headers=user_b["headers"]
    )
    assert resp.status_code == 404

    # List is scoped per user.
    resp = await client.get("/knowledge/conversations", headers=user_a["headers"])
    assert len(resp.json()) == 1
    resp = await client.get("/knowledge/conversations", headers=user_b["headers"])
    assert len(resp.json()) == 0


async def test_continue_conversation(client):
    user = await create_user("u@kb.com", UserRole.candidat)
    first = await client.post(
        "/knowledge/ask", headers=user["headers"], json={"question": "Premiere question?"}
    )
    conv_id = first.json()["conversation_id"]
    second = await client.post(
        "/knowledge/ask",
        headers=user["headers"],
        json={"question": "Deuxieme question?", "conversation_id": conv_id},
    )
    assert second.json()["conversation_id"] == conv_id
    resp = await client.get(
        f"/knowledge/conversations/{conv_id}", headers=user["headers"]
    )
    assert len(resp.json()["messages"]) == 4


async def test_delete_conversation(client):
    user = await create_user("u@kb.com", UserRole.candidat)
    ask = await client.post(
        "/knowledge/ask", headers=user["headers"], json={"question": "Q?"}
    )
    conv_id = ask.json()["conversation_id"]
    resp = await client.delete(
        f"/knowledge/conversations/{conv_id}", headers=user["headers"]
    )
    assert resp.status_code == 200
    resp = await client.get(
        f"/knowledge/conversations/{conv_id}", headers=user["headers"]
    )
    assert resp.status_code == 404
