"""Add compliance details columns to dossiers

Revision ID: 005
Revises: 004
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dossiers",
        sa.Column("compliance_details", sa.JSON(), nullable=True),
    )
    op.add_column(
        "dossiers",
        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("dossiers", "last_verified_at")
    op.drop_column("dossiers", "compliance_details")
