"""Create ircc_updates table.

Revision ID: 004
Revises: 003
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ircc_updates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "new_program", "criteria_change", "processing_time",
                "policy_update", "fee_change", "form_update", "general_news",
                name="irccupdatecategory",
            ),
            nullable=False,
            server_default="general_news",
        ),
        sa.Column(
            "source",
            sa.Enum("atom_feed", "processing_times", "manual", name="irccupdatesource"),
            nullable=False,
            server_default="atom_feed",
        ),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("external_id", sa.String(255), unique=True, nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ircc_updates_category", "ircc_updates", ["category"])
    op.create_index("ix_ircc_updates_detected_at", "ircc_updates", ["detected_at"])


def downgrade() -> None:
    op.drop_index("ix_ircc_updates_detected_at", table_name="ircc_updates")
    op.drop_index("ix_ircc_updates_category", table_name="ircc_updates")
    op.drop_table("ircc_updates")
    op.execute("DROP TYPE IF EXISTS irccupdatecategory")
    op.execute("DROP TYPE IF EXISTS irccupdatesource")
