"""Create billing tables (invoices, line items, payments).

Revision ID: 013
Revises: 012
"""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    invoice_status = sa.Enum(
        "draft", "sent", "paid", "partially_paid", "overdue", "cancelled",
        name="invoicestatus",
    )
    line_item_kind = sa.Enum(
        "service_fee", "government_fee", "other", name="lineitemkind"
    )
    payment_status = sa.Enum(
        "pending", "succeeded", "failed", "refunded", name="paymentstatus"
    )
    payment_method = sa.Enum("stripe", "manual", name="paymentmethod")

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("invoice_number", sa.String(50), nullable=False, unique=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", invoice_status, nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="cad"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Float(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("kind", line_item_kind, nullable=False, server_default="service_fee"),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="cad"),
        sa.Column("method", payment_method, nullable=False, server_default="stripe"),
        sa.Column("status", payment_status, nullable=False, server_default="pending"),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
    for name in ("invoicestatus", "lineitemkind", "paymentstatus", "paymentmethod"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
