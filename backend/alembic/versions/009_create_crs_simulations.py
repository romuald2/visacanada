"""Create CRS simulations table.

Revision ID: 009
Revises: 008
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crs_simulations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("calculated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("crs_simulations")
