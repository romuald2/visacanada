"""Create deadlines table and extend alerttype enum.

Adds the immigration deadline engine's storage (Lot 3): a `deadlines`
table for time-sensitive milestones (ITA response, biometrics, PPR,
permit expiries) plus new `alerttype` enum values the deadline scan emits.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

# New alerttype values emitted by the deadline scan.
_NEW_ALERT_TYPES = (
    "ita_response",
    "biometrics",
    "ppr",
    "medical_request",
    "permit_expiring",
)


def upgrade() -> None:
    bind = op.get_bind()

    deadline_type = sa.Enum(
        "ita_response",
        "biometrics",
        "ppr",
        "medical_request",
        "submission",
        "work_permit_expiry",
        "study_permit_expiry",
        "custom",
        name="deadlinetype",
    )
    deadline_source = sa.Enum("manual", "derived", name="deadlinesource")

    op.create_table(
        "deadlines",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "dossier_id",
            sa.Integer(),
            sa.ForeignKey("dossiers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("deadline_type", deadline_type, nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "source", deadline_source, nullable=False, server_default="manual"
        ),
        sa.Column(
            "is_completed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_deadlines_dossier_id", "deadlines", ["dossier_id"])

    # Extend the existing alerttype enum (Postgres only; SQLite stores enums
    # as plain strings so no ALTER is needed there).
    if bind.dialect.name == "postgresql":
        for value in _NEW_ALERT_TYPES:
            op.execute(f"ALTER TYPE alerttype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    op.drop_index("ix_deadlines_dossier_id", table_name="deadlines")
    op.drop_table("deadlines")
    sa.Enum(name="deadlinetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="deadlinesource").drop(op.get_bind(), checkfirst=True)
    # Note: Postgres cannot easily remove enum values; the added alerttype
    # values are left in place on downgrade (harmless).
