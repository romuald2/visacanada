"""create core tables (candidates, programs, dossiers, documents, notifications, audit_logs)

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types
    immigration_program_enum = sa.Enum(
        "express_entry_fsw", "express_entry_cec", "express_entry_fst",
        "pnp", "iec_working_holiday", "iec_young_professionals", "iec_coop",
        "study_permit", "work_permit_lmia", "work_permit_imp",
        "family_spouse", "family_parent", "family_child",
        "super_visa", "visitor_visa", "refugee",
        name="immigrationprogram",
    )
    immigration_program_enum.create(op.get_bind(), checkfirst=True)

    dossier_status_enum = sa.Enum(
        "nouveau", "en_cours", "documents_manquants", "en_revision",
        "soumis", "approuve", "refuse", "archive",
        name="dossierstatus",
    )
    dossier_status_enum.create(op.get_bind(), checkfirst=True)

    document_type_enum = sa.Enum(
        "passport", "birth_certificate", "photo", "language_test",
        "education_credential", "work_reference", "bank_statement",
        "police_certificate", "medical_exam", "travel_history",
        "employment_letter", "invitation_letter", "proof_of_funds",
        "marriage_certificate", "cv_resume", "cover_letter", "other",
        name="documenttype",
    )
    document_type_enum.create(op.get_bind(), checkfirst=True)

    document_status_enum = sa.Enum(
        "pending", "uploaded", "analyzing", "verified",
        "rejected", "expired", "fraud_suspected",
        name="documentstatus",
    )
    document_status_enum.create(op.get_bind(), checkfirst=True)

    notification_type_enum = sa.Enum(
        "email_ircc", "document_missing", "document_verified", "document_rejected",
        "deadline_approaching", "status_change", "policy_update",
        "payment_reminder", "system",
        name="notificationtype",
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)

    notification_channel_enum = sa.Enum(
        "dashboard", "whatsapp", "email", "sms",
        name="notificationchannel",
    )
    notification_channel_enum.create(op.get_bind(), checkfirst=True)

    # Programs table
    op.create_table(
        "programs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("code", immigration_program_enum, unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("processing_time_days", sa.Integer(), nullable=True),
        sa.Column("government_fee", sa.Float(), nullable=True),
        sa.Column("documents_required", sa.Text(), nullable=True),
        sa.Column("eligibility_criteria", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Candidates table
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("passport_number", sa.String(50), nullable=True),
        sa.Column("current_country", sa.String(100), nullable=True),
        sa.Column("current_city", sa.String(100), nullable=True),
        sa.Column("language_french", sa.String(10), nullable=True),
        sa.Column("language_english", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Dossiers table
    op.create_table(
        "dossiers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id"), nullable=False),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", dossier_status_enum, nullable=False, server_default="nouveau"),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("document_type", document_type_enum, nullable=False),
        sa.Column("status", document_status_enum, nullable=False, server_default="pending"),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path_s3", sa.String(512), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("fraud_score", sa.Float(), nullable=True),
        sa.Column("extracted_data", sa.Text(), nullable=True),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=True),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("channel", notification_channel_enum, nullable=False, server_default="dashboard"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("documents")
    op.drop_table("dossiers")
    op.drop_table("candidates")
    op.drop_table("programs")
    sa.Enum(name="notificationchannel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notificationtype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="documentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="documenttype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="dossierstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="immigrationprogram").drop(op.get_bind(), checkfirst=True)
