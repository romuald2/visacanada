"""Create program_requirements and requirement_changes tables.

Revision ID: 003
Revises: 002
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "program_requirements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id"), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("mandatory", "recommended", "optional", name="requirementpriority"),
            nullable=False,
            server_default="mandatory",
        ),
        sa.Column("imm_form_reference", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_program_requirements_program_id",
        "program_requirements",
        ["program_id"],
    )

    op.create_table(
        "requirement_changes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "requirement_id",
            sa.Integer(),
            sa.ForeignKey("program_requirements.id"),
            nullable=False,
        ),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_requirement_changes_requirement_id",
        "requirement_changes",
        ["requirement_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_requirement_changes_requirement_id", table_name="requirement_changes")
    op.drop_table("requirement_changes")
    op.drop_index("ix_program_requirements_program_id", table_name="program_requirements")
    op.drop_table("program_requirements")
    op.execute("DROP TYPE IF EXISTS requirementpriority")
