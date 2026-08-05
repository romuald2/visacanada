"""Knowledge-base & chatbot API (IRCC RAG assistant).

- Ingestion of source documents (admin/consultant): chunk + embed + store.
- Chat: retrieve relevant chunks, generate a grounded answer with citations,
  and persist the conversation history.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.knowledge import (
    ChatConversation,
    ChatMessage,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSourceType,
    MessageRole,
)
from app.models.user import User, UserRole
from app.services.rag_service import content_hash, rag_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_editor_roles = require_role(UserRole.admin, UserRole.consultant)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class IngestRequest(BaseModel):
    title: str
    content: str
    source_type: str = "manual"
    source_url: str | None = None
    language: str = "fr"


class AskRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    top_k: int = 5


# --------------------------------------------------------------------------- #
# Ingestion (admin/consultant)
# --------------------------------------------------------------------------- #
@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def ingest_document(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_editor_roles),
):
    """Ingest (or re-ingest) a source document into the knowledge base."""
    try:
        source_type = KnowledgeSourceType(body.source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type de source invalide: {body.source_type}")

    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Contenu vide")

    new_hash = content_hash(body.content)

    # If a document with the same URL exists and content is unchanged, skip.
    existing = None
    if body.source_url:
        res = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.source_url == body.source_url)
        )
        existing = res.scalar_one_or_none()

    if existing is not None:
        if existing.content_hash == new_hash:
            return {
                "detail": "Document inchange, ingestion ignoree",
                "document_id": existing.id,
                "reingested": False,
                "chunk_count": existing.chunk_count,
            }
        # Content changed: drop old chunks and re-ingest.
        await db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == existing.id)
        )
        doc = existing
        doc.title = body.title
        doc.content_hash = new_hash
        doc.language = body.language
        doc.source_type = source_type
        doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        reingested = True
    else:
        doc = KnowledgeDocument(
            title=body.title,
            source_type=source_type,
            source_url=body.source_url,
            content_hash=new_hash,
            language=body.language,
        )
        db.add(doc)
        reingested = False

    await db.flush()

    chunks = rag_service.chunk_text(body.content)
    if not chunks:
        raise HTTPException(status_code=400, detail="Aucun chunk genere")

    embeddings = await rag_service.embed_batch(chunks)
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        db.add(
            KnowledgeChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk,
                embedding=emb,
                token_estimate=rag_service.estimate_tokens(chunk),
            )
        )
    doc.chunk_count = len(chunks)
    await db.commit()
    await db.refresh(doc)

    return {
        "detail": "Document ingere",
        "document_id": doc.id,
        "reingested": reingested,
        "chunk_count": doc.chunk_count,
        "embedding_method": "voyage" if rag_service.embedding_available else "local",
    }


@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_editor_roles),
):
    """List ingested knowledge-base documents."""
    res = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc())
    )
    docs = res.scalars().all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "source_type": d.source_type.value
            if hasattr(d.source_type, "value")
            else d.source_type,
            "source_url": d.source_url,
            "language": d.language,
            "chunk_count": d.chunk_count,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
        for d in docs
    ]


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_editor_roles),
):
    """Delete a document and its chunks."""
    res = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    doc = res.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document non trouve")
    await db.delete(doc)
    await db.commit()
    return {"detail": "Document supprime"}
# --------------------------------------------------------------------------- #
# Retrieval helper
# --------------------------------------------------------------------------- #
async def _retrieve(question: str, top_k: int, db: AsyncSession) -> list[dict]:
    """Retrieve and rank the most relevant chunks for a question."""
    query_vec = await rag_service.embed(question)
    res = await db.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
    )
    rows = res.all()
    candidates = [
        {
            "chunk_id": chunk.id,
            "document_id": doc.id,
            "title": doc.title,
            "source_url": doc.source_url,
            "content": chunk.content,
            "embedding": chunk.embedding,
        }
        for chunk, doc in rows
    ]
    return rag_service.rank_chunks(question, query_vec, candidates, top_k=top_k)


# --------------------------------------------------------------------------- #
# Chat (any authenticated user)
# --------------------------------------------------------------------------- #
@router.post("/ask")
async def ask(
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Answer a question using RAG and persist it to a conversation."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    # Resolve or create the conversation (must belong to the user).
    if body.conversation_id is not None:
        res = await db.execute(
            select(ChatConversation).where(ChatConversation.id == body.conversation_id)
        )
        conversation = res.scalar_one_or_none()
        if conversation is None or conversation.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Conversation non trouvee")
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=body.question[:60],
        )
        db.add(conversation)
        await db.flush()

    top_chunks = await _retrieve(body.question, body.top_k, db)
    result = await rag_service.generate_answer(body.question, top_chunks)

    # Build de-duplicated citations by document.
    citations = []
    seen_docs = set()
    for c in top_chunks:
        if c["document_id"] in seen_docs:
            continue
        seen_docs.add(c["document_id"])
        citations.append(
            {
                "document_id": c["document_id"],
                "title": c["title"],
                "source_url": c["source_url"],
                "score": c["score"],
            }
        )

    # Persist user + assistant messages.
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=body.question,
        )
    )
    assistant_msg = ChatMessage(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=result["answer"],
        citations=citations,
        method=result["method"],
    )
    db.add(assistant_msg)
    conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(assistant_msg)

    return {
        "conversation_id": conversation.id,
        "message_id": assistant_msg.id,
        "answer": result["answer"],
        "method": result["method"],
        "citations": citations,
    }


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's conversations."""
    res = await db.execute(
        select(ChatConversation)
        .where(ChatConversation.user_id == current_user.id)
        .order_by(ChatConversation.updated_at.desc())
    )
    convos = res.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convos
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a conversation with its full message history."""
    res = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    conversation = res.scalar_one_or_none()
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation non trouvee")

    msg_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    messages = msg_res.scalars().all()
    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role.value if hasattr(m.role, "value") else m.role,
                "content": m.content,
                "citations": m.citations or [],
                "method": m.method,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of the current user's conversations."""
    res = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    conversation = res.scalar_one_or_none()
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation non trouvee")
    await db.delete(conversation)
    await db.commit()
    return {"detail": "Conversation supprimee"}
