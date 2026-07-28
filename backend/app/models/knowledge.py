"""Knowledge base models for the IRCC RAG chatbot.

Stores ingested source documents, their semantically chunked text with
embeddings, and conversation history. Embeddings are persisted as JSON so the
storage layer stays portable across PostgreSQL (prod) and SQLite (tests);
similarity is computed in Python at query time.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class KnowledgeSourceType(str, Enum):
    ircc_page = "ircc_page"
    policy = "policy"
    manual = "manual"
    faq = "faq"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class KnowledgeDocument(Base):
    """A source document ingested into the knowledge base."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[KnowledgeSourceType] = mapped_column(
        String(50), default=KnowledgeSourceType.manual, nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Hash of the source content to detect changes and avoid re-ingestion.
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(10), default="fr", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    """A semantic chunk of a document with its embedding vector."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Embedding vector stored as a JSON list of floats.
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")


class ChatConversation(Base):
    """A chatbot conversation belonging to a user."""

    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), default="Nouvelle conversation", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """A single message within a conversation, with source citations."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Citations: list of {document_id, title, source_url, score}.
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    conversation: Mapped["ChatConversation"] = relationship(back_populates="messages")
