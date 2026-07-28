"""Add ON DELETE CASCADE to requirement_changes.requirement_id.

Deleting a ProgramRequirement must also delete its change history. The
column is NOT NULL, so the previous default (no cascade) caused a
violation when a requirement with history was removed. The ORM handles
this in Python via cascade="all, delete-orphan"; this migration keeps the
database-level constraint consistent for Postgres.

Revision ID: 016
Revises: 015
"""

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

# Postgres auto-names FKs as <table>_<column>_fkey.
_FK_NAME = "requirement_changes_requirement_id_fkey"


def upgrade() -> None:
    bind = op.get_bind()
    # SQLite cannot ALTER a constraint; the ORM cascade covers it there.
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(_FK_NAME, "requirement_changes", type_="foreignkey")
    op.create_foreign_key(
        _FK_NAME,
        "requirement_changes",
        "program_requirements",
        ["requirement_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(_FK_NAME, "requirement_changes", type_="foreignkey")
    op.create_foreign_key(
        _FK_NAME,
        "requirement_changes",
        "program_requirements",
        ["requirement_id"],
        ["id"],
    )
