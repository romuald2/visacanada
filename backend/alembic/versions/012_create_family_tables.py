"""Create family group tables.

Revision ID: 012
Revises: 011
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "family_groups",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("principal_candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    family_role = sa.Enum(
        "principal", "conjoint", "enfant", "autre", name="familyrole"
    )
    op.create_table(
        "family_members",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("family_group_id", sa.Integer(), sa.ForeignKey("family_groups.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("role", family_role, nullable=False, server_default="autre"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "shared_documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("family_group_id", sa.Integer(), sa.ForeignKey("family_groups.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("shared_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("shared_documents")
    op.drop_table("family_members")
    op.drop_table("family_groups")
    sa.Enum(name="familyrole").drop(op.get_bind(), checkfirst=True)
