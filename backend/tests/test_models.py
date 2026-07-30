"""Tests for all database models."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.dossier import Dossier, DossierStatus
from app.models.notification import Notification, NotificationChannel, NotificationType
from app.models.program import ImmigrationProgram, Program
from app.models.user import Base, User, UserRole
from app.seeds import PROGRAMS_SEED
from app.seeds.seed_programs import seed_programs

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session():
    async with TestSessionLocal() as session:
        yield session


# --- User Model Tests ---


class TestUserModel:
    async def test_create_user(self, session: AsyncSession):
        user = User(
            email="test@example.com",
            hashed_password="hashedpass123",
            full_name="Test User",
            role=UserRole.candidat,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.candidat
        assert user.is_active is True

    async def test_user_role_enum(self):
        assert UserRole.admin == "admin"
        assert UserRole.consultant == "consultant"
        assert UserRole.candidat == "candidat"
        assert len(UserRole) == 3

    async def test_user_unique_email(self, session: AsyncSession):
        user1 = User(
            email="dup@example.com",
            hashed_password="hash1",
            full_name="User One",
        )
        session.add(user1)
        await session.commit()

        user2 = User(
            email="dup@example.com",
            hashed_password="hash2",
            full_name="User Two",
        )
        session.add(user2)
        with pytest.raises(Exception):
            await session.commit()

    async def test_user_repr(self, session: AsyncSession):
        user = User(
            email="repr@test.com",
            hashed_password="hash",
            full_name="Repr Test",
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert "repr@test.com" in repr(user)
        assert "admin" in repr(user)


# --- Program Model Tests ---


class TestProgramModel:
    async def test_create_program(self, session: AsyncSession):
        program = Program(
            code=ImmigrationProgram.express_entry_fsw,
            name="Federal Skilled Worker",
            category="Express Entry",
            description="Test program",
            processing_time_days=180,
            government_fee=1365.0,
            is_active=True,
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)

        assert program.id is not None
        assert program.code == ImmigrationProgram.express_entry_fsw
        assert program.name == "Federal Skilled Worker"
        assert program.category == "Express Entry"
        assert program.processing_time_days == 180
        assert program.government_fee == 1365.0

    async def test_immigration_program_enum(self):
        assert len(ImmigrationProgram) == 16
        assert ImmigrationProgram.express_entry_fsw == "express_entry_fsw"
        assert ImmigrationProgram.pnp == "pnp"
        assert ImmigrationProgram.study_permit == "study_permit"
        assert ImmigrationProgram.refugee == "refugee"

    async def test_program_repr(self, session: AsyncSession):
        program = Program(
            code=ImmigrationProgram.pnp,
            name="PNP",
            category="PNP",
            is_active=True,
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)

        assert "PNP" in repr(program)

    async def test_seed_programs(self, session: AsyncSession):
        created = await seed_programs(session)
        assert created == 16
        assert created == len(PROGRAMS_SEED)

    async def test_seed_programs_idempotent(self, session: AsyncSession):
        await seed_programs(session)
        created_second = await seed_programs(session)
        assert created_second == 0


# --- Candidate Model Tests ---


class TestCandidateModel:
    async def test_create_candidate(self, session: AsyncSession):
        candidate = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            phone="+33612345678",
            date_of_birth=date(1990, 5, 15),
            nationality="Française",
            passport_number="FR123456",
            current_country="France",
            current_city="Paris",
            language_french="CLB 10",
            language_english="CLB 7",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        assert candidate.id is not None
        assert candidate.first_name == "Jean"
        assert candidate.last_name == "Dupont"
        assert candidate.nationality == "Française"
        assert candidate.date_of_birth == date(1990, 5, 15)

    async def test_candidate_linked_to_user(self, session: AsyncSession):
        user = User(
            email="candidate@test.com",
            hashed_password="hash",
            full_name="Candidate User",
            role=UserRole.candidat,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        candidate = Candidate(
            user_id=user.id,
            first_name="Marie",
            last_name="Tremblay",
            email="candidate@test.com",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        assert candidate.user_id == user.id

    async def test_candidate_repr(self, session: AsyncSession):
        candidate = Candidate(
            first_name="Pierre",
            last_name="Martin",
            email="pierre@test.com",
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        assert "Pierre" in repr(candidate)
        assert "Martin" in repr(candidate)


# --- Dossier Model Tests ---


class TestDossierModel:
    async def test_create_dossier(self, session: AsyncSession):
        # Setup candidate and program
        candidate = Candidate(
            first_name="Ali", last_name="Hassan", email="ali@test.com"
        )
        program = Program(
            code=ImmigrationProgram.study_permit,
            name="Permis d'études",
            category="Études",
            is_active=True,
        )
        session.add_all([candidate, program])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.nouveau,
            notes="Nouveau dossier de test",
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        assert dossier.id is not None
        assert dossier.status == DossierStatus.nouveau
        assert dossier.candidate_id == candidate.id
        assert dossier.program_id == program.id
        assert dossier.compliance_score is None

    async def test_dossier_status_enum(self):
        assert len(DossierStatus) == 8
        assert DossierStatus.nouveau == "nouveau"
        assert DossierStatus.en_cours == "en_cours"
        assert DossierStatus.soumis == "soumis"
        assert DossierStatus.approuve == "approuve"
        assert DossierStatus.refuse == "refuse"

    async def test_dossier_with_assigned_consultant(self, session: AsyncSession):
        consultant = User(
            email="consultant@test.com",
            hashed_password="hash",
            full_name="Consultant",
            role=UserRole.consultant,
        )
        candidate = Candidate(
            first_name="Test", last_name="Cand", email="cand@test.com"
        )
        program = Program(
            code=ImmigrationProgram.visitor_visa,
            name="Visa visiteur",
            category="Temporaire",
            is_active=True,
        )
        session.add_all([consultant, candidate, program])
        await session.commit()
        await session.refresh(consultant)
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            assigned_to=consultant.id,
            status=DossierStatus.en_cours,
            compliance_score=75.5,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        assert dossier.assigned_to == consultant.id
        assert dossier.compliance_score == 75.5

    async def test_dossier_repr(self, session: AsyncSession):
        candidate = Candidate(
            first_name="X", last_name="Y", email="xy@test.com"
        )
        program = Program(
            code=ImmigrationProgram.express_entry_cec,
            name="CEC",
            category="Express Entry",
            is_active=True,
        )
        session.add_all([candidate, program])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.en_revision,
            compliance_score=88.0,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        assert "en_revision" in repr(dossier)
        assert "88.0" in repr(dossier)


# --- Document Model Tests ---


class TestDocumentModel:
    async def test_create_document(self, session: AsyncSession):
        candidate = Candidate(
            first_name="Doc", last_name="Test", email="doc@test.com"
        )
        program = Program(
            code=ImmigrationProgram.work_permit_lmia,
            name="Work Permit LMIA",
            category="Travail",
            is_active=True,
        )
        session.add_all([candidate, program])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.nouveau,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        document = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.passport,
            status=DocumentStatus.uploaded,
            file_name="passport_scan.pdf",
            file_path_s3="s3://bucket/docs/passport_scan.pdf",
            file_size_bytes=2048576,
            mime_type="application/pdf",
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)

        assert document.id is not None
        assert document.document_type == DocumentType.passport
        assert document.status == DocumentStatus.uploaded
        assert document.file_name == "passport_scan.pdf"
        assert document.file_size_bytes == 2048576

    async def test_document_type_enum(self):
        assert len(DocumentType) == 17
        assert DocumentType.passport == "passport"
        assert DocumentType.language_test == "language_test"
        assert DocumentType.other == "other"

    async def test_document_status_enum(self):
        assert len(DocumentStatus) == 7
        assert DocumentStatus.pending == "pending"
        assert DocumentStatus.verified == "verified"
        assert DocumentStatus.fraud_suspected == "fraud_suspected"

    async def test_document_with_ai_analysis(self, session: AsyncSession):
        candidate = Candidate(
            first_name="AI", last_name="Test", email="ai@test.com"
        )
        program = Program(
            code=ImmigrationProgram.family_spouse,
            name="Parrainage conjoint",
            category="Famille",
            is_active=True,
        )
        session.add_all([candidate, program])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.en_revision,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        document = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.marriage_certificate,
            status=DocumentStatus.verified,
            file_name="marriage_cert.pdf",
            compliance_score=95.0,
            fraud_score=2.5,
            ai_analysis='{"valid": true, "issues": []}',
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)

        assert document.compliance_score == 95.0
        assert document.fraud_score == 2.5
        assert document.ai_analysis is not None

    async def test_document_repr(self, session: AsyncSession):
        candidate = Candidate(
            first_name="R", last_name="T", email="rt@test.com"
        )
        program = Program(
            code=ImmigrationProgram.super_visa,
            name="Super Visa",
            category="Famille",
            is_active=True,
        )
        session.add_all([candidate, program])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            status=DossierStatus.nouveau,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        doc = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.bank_statement,
            status=DocumentStatus.analyzing,
            file_name="bank.pdf",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert "bank_statement" in repr(doc)
        assert "analyzing" in repr(doc)


# --- Notification Model Tests ---


class TestNotificationModel:
    async def test_create_notification(self, session: AsyncSession):
        user = User(
            email="notif@test.com",
            hashed_password="hash",
            full_name="Notif User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        notification = Notification(
            recipient_id=user.id,
            notification_type=NotificationType.email_ircc,
            channel=NotificationChannel.whatsapp,
            title="Nouvel email IRCC",
            message="Vous avez reçu un email d'IRCC concernant votre dossier.",
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        assert notification.id is not None
        assert notification.notification_type == NotificationType.email_ircc
        assert notification.channel == NotificationChannel.whatsapp
        assert notification.is_read is False
        assert notification.title == "Nouvel email IRCC"

    async def test_notification_type_enum(self):
        assert len(NotificationType) == 9
        assert NotificationType.email_ircc == "email_ircc"
        assert NotificationType.document_missing == "document_missing"
        assert NotificationType.policy_update == "policy_update"

    async def test_notification_channel_enum(self):
        assert len(NotificationChannel) == 4
        assert NotificationChannel.dashboard == "dashboard"
        assert NotificationChannel.whatsapp == "whatsapp"
        assert NotificationChannel.email == "email"
        assert NotificationChannel.sms == "sms"

    async def test_notification_repr(self, session: AsyncSession):
        user = User(
            email="repr_notif@test.com",
            hashed_password="hash",
            full_name="Repr Notif",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        notif = Notification(
            recipient_id=user.id,
            notification_type=NotificationType.deadline_approaching,
            channel=NotificationChannel.dashboard,
            title="Échéance proche",
            message="Votre permis expire dans 30 jours.",
        )
        session.add(notif)
        await session.commit()
        await session.refresh(notif)

        assert "deadline_approaching" in repr(notif)


# --- AuditLog Model Tests ---


class TestAuditLogModel:
    async def test_create_audit_log(self, session: AsyncSession):
        user = User(
            email="audit@test.com",
            hashed_password="hash",
            full_name="Audit User",
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        log = AuditLog(
            user_id=user.id,
            action="create",
            entity_type="dossier",
            entity_id=1,
            details="Création du dossier #1 pour le candidat Jean Dupont",
            ip_address="192.168.1.100",
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)

        assert log.id is not None
        assert log.action == "create"
        assert log.entity_type == "dossier"
        assert log.entity_id == 1
        assert log.ip_address == "192.168.1.100"

    async def test_audit_log_without_user(self, session: AsyncSession):
        log = AuditLog(
            user_id=None,
            action="system_startup",
            entity_type="system",
            details="Application démarrée",
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)

        assert log.id is not None
        assert log.user_id is None
        assert log.action == "system_startup"

    async def test_audit_log_repr(self, session: AsyncSession):
        log = AuditLog(
            action="delete",
            entity_type="document",
            entity_id=42,
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)

        assert "delete" in repr(log)
        assert "document" in repr(log)


# --- Relationships Tests ---


class TestRelationships:
    async def test_dossier_relationships(self, session: AsyncSession):
        """Test that dossier correctly links candidate, program, and documents."""
        user = User(
            email="rel@test.com",
            hashed_password="hash",
            full_name="Rel User",
            role=UserRole.consultant,
        )
        candidate = Candidate(
            first_name="Rel", last_name="Cand", email="relcand@test.com"
        )
        program = Program(
            code=ImmigrationProgram.iec_working_holiday,
            name="PVT",
            category="IEC",
            is_active=True,
        )
        session.add_all([user, candidate, program])
        await session.commit()
        await session.refresh(user)
        await session.refresh(candidate)
        await session.refresh(program)

        dossier = Dossier(
            candidate_id=candidate.id,
            program_id=program.id,
            assigned_to=user.id,
            status=DossierStatus.en_cours,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        doc = Document(
            dossier_id=dossier.id,
            document_type=DocumentType.passport,
            status=DocumentStatus.uploaded,
            file_name="passport.pdf",
            uploaded_by=user.id,
        )
        session.add(doc)
        await session.commit()

        assert dossier.candidate_id == candidate.id
        assert dossier.program_id == program.id
        assert dossier.assigned_to == user.id
        assert doc.dossier_id == dossier.id
        assert doc.uploaded_by == user.id

    async def test_candidate_multiple_dossiers(self, session: AsyncSession):
        """A candidate can have multiple dossiers for different programs."""
        candidate = Candidate(
            first_name="Multi", last_name="Dossier", email="multi@test.com"
        )
        program1 = Program(
            code=ImmigrationProgram.study_permit,
            name="Études",
            category="Études",
            is_active=True,
        )
        program2 = Program(
            code=ImmigrationProgram.work_permit_imp,
            name="IMP",
            category="Travail",
            is_active=True,
        )
        session.add_all([candidate, program1, program2])
        await session.commit()
        await session.refresh(candidate)
        await session.refresh(program1)
        await session.refresh(program2)

        dossier1 = Dossier(
            candidate_id=candidate.id,
            program_id=program1.id,
            status=DossierStatus.soumis,
        )
        dossier2 = Dossier(
            candidate_id=candidate.id,
            program_id=program2.id,
            status=DossierStatus.nouveau,
        )
        session.add_all([dossier1, dossier2])
        await session.commit()

        from sqlalchemy import select
        stmt = select(Dossier).where(Dossier.candidate_id == candidate.id)
        result = await session.execute(stmt)
        dossiers = result.scalars().all()

        assert len(dossiers) == 2
