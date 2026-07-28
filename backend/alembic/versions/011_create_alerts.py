"""Create alerts and alert_configs tables.

Revision ID: 011
Revises: 010
"""

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_configs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=False, unique=True),
        sa.Column("enabled_types", sa.JSON(), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    alert_type = sa.Enum(
        "passport_expiring",
        "medical_expiring",
        "language_expiring",
        "express_entry_round",
        "policy_change",
        "submission_deadline",
        name="alerttype",
    )
    alert_severity = sa.Enum("info", "warning", "critical", name="alertseverity")

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("alert_type", alert_type, nullable=False),
        sa.Column("severity", alert_severity, nullable=False, server_default="info"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("dedup_key", sa.String(255), nullable=False, index=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_notified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alerts_dedup_key", "alerts", ["dedup_key"])


def downgrade() -> None:
    op.drop_index("ix_alerts_dedup_key", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("alert_configs")
    sa.Enum(name="alerttype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="alertseverity").drop(op.get_bind(), checkfirst=True)
