"""Create fraud_analyses table

Revision ID: 006
Revises: 005
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fraud_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("fraud_score", sa.Float(), nullable=False, default=0.0),
        sa.Column(
            "risk_level",
            sa.Enum("negligible", "low", "medium", "high", "critical", name="fraudrisklevel"),
            nullable=False,
            server_default="negligible",
        ),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, default=False),
        sa.Column("alerts", sa.JSON(), nullable=True),
        sa.Column("alerts_count", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending_review", "reviewed_legitimate", "reviewed_suspicious", "reviewed_fraudulent", name="fraudalertstatus"),
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fraud_analyses_document_id", "fraud_analyses", ["document_id"])
    op.create_index("ix_fraud_analyses_risk_level", "fraud_analyses", ["risk_level"])
    op.create_index("ix_fraud_analyses_status", "fraud_analyses", ["status"])


def downgrade() -> None:
    op.drop_index("ix_fraud_analyses_status")
    op.drop_index("ix_fraud_analyses_risk_level")
    op.drop_index("ix_fraud_analyses_document_id")
    op.drop_table("fraud_analyses")
    op.execute("DROP TYPE IF EXISTS fraudrisklevel")
    op.execute("DROP TYPE IF EXISTS fraudalertstatus")
