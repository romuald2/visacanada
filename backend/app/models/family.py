"""Family dossier models: link multiple candidates with shared documents."""

from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class FamilyRole(str, enum.Enum):
    principal = "principal"
    conjoint = "conjoint"
    enfant = "enfant"
    autre = "autre"


class FamilyGroup(Base):
    """A family group linking several candidates for coordinated processing."""

    __tablename__ = "family_groups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    principal_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FamilyGroup(id={self.id}, name={self.name})>"


class FamilyMember(Base):
    """Membership of a candidate in a family group with a role."""

    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_group_id: Mapped[int] = mapped_column(
        ForeignKey("family_groups.id"), nullable=False
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"), nullable=False
    )
    role: Mapped[FamilyRole] = mapped_column(
        Enum(FamilyRole), default=FamilyRole.autre, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FamilyMember(group={self.family_group_id}, candidate={self.candidate_id}, role={self.role})>"


class SharedDocument(Base):
    """A document shared across a family group (e.g. proof of funds, address)."""

    __tablename__ = "shared_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_group_id: Mapped[int] = mapped_column(
        ForeignKey("family_groups.id"), nullable=False
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False
    )
    shared_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SharedDocument(group={self.family_group_id}, doc={self.document_id})>"
