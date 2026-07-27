"""Create email_connections and ircc_emails tables

Revision ID: 007
Revises: 006
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_connections",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("provider", sa.Enum("gmail", "outlook", name="emailprovider"), nullable=False),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("consent_revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_connections_candidate_id", "email_connections", ["candidate_id"])

    op.create_table(
        "ircc_emails",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=True),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("email_connections.id"), nullable=False),
        sa.Column("message_id", sa.String(255), unique=True, nullable=False),
        sa.Column("sender", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_preview", sa.Text(), nullable=True),
        sa.Column("notification_type", sa.String(100), nullable=True),
        sa.Column("action_required", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, default=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ircc_emails_candidate_id", "ircc_emails", ["candidate_id"])
    op.create_index("ix_ircc_emails_dossier_id", "ircc_emails", ["dossier_id"])


def downgrade() -> None:
    op.drop_index("ix_ircc_emails_dossier_id")
    op.drop_index("ix_ircc_emails_candidate_id")
    op.drop_table("ircc_emails")
    op.drop_index("ix_email_connections_candidate_id")
    op.drop_table("email_connections")
    op.execute("DROP TYPE IF EXISTS emailprovider")
