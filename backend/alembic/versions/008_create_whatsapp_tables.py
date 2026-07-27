"""Create whatsapp_notifications and notification_preferences tables

Revision ID: 008
Revises: 007
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("to_number", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("sent", "failed", "rate_limited", "skipped", name="notificationstatus"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("twilio_sid", sa.String(100), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_whatsapp_notifications_user_id", "whatsapp_notifications", ["user_id"])
    op.create_index("ix_whatsapp_notifications_event_type", "whatsapp_notifications", ["event_type"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("whatsapp_number", sa.String(50), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("events", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_index("ix_whatsapp_notifications_event_type")
    op.drop_index("ix_whatsapp_notifications_user_id")
    op.drop_table("whatsapp_notifications")
    op.execute("DROP TYPE IF EXISTS notificationstatus")
