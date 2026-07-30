"""Tests for email integration system."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.candidate import Candidate
from app.models.email_connection import EmailConnection, EmailProvider, IRCCEmail
from app.models.user import Base, User, UserRole
from app.services.email_service import EmailService, GmailService, OutlookService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def setup_candidate_with_connection() -> tuple[int, int, dict]:
    """Create admin + candidate + email connection. Return (candidate_id, connection_id, headers)."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@email.com",
            hashed_password=hash_password("pass"),
            full_name="Admin Email",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        candidate = Candidate(first_name="Jean", last_name="Dupont", email="jean@test.com")
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        connection = EmailConnection(
            candidate_id=candidate.id,
            provider=EmailProvider.gmail,
            email_address="jean.dupont@gmail.com",
            access_token="fake_access_token",
            refresh_token="fake_refresh_token",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True,
        )
        session.add(connection)
        await session.commit()
        await session.refresh(connection)

        token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}

        return candidate.id, connection.id, headers


# =============================================================================
# EmailService Unit Tests
# =============================================================================


class TestEmailService:
    """Unit tests for email service logic."""

    def test_filter_ircc_emails(self):
        """Filter should only keep IRCC domain emails."""
        service = EmailService()
        emails = [
            {"sender": "noreply@cic.gc.ca", "subject": "Decision"},
            {"sender": "user@gmail.com", "subject": "Hello"},
            {"sender": "updates@canada.ca", "subject": "Update"},
            {"sender": "spam@example.com", "subject": "Buy now"},
        ]
        filtered = service.filter_ircc_emails(emails)
        assert len(filtered) == 2
        assert filtered[0]["sender"] == "noreply@cic.gc.ca"
        assert filtered[1]["sender"] == "updates@canada.ca"

    def test_filter_case_insensitive(self):
        """Filter should work case-insensitively."""
        service = EmailService()
        emails = [
            {"sender": "NoReply@CIC.GC.CA", "subject": "Test"},
        ]
        filtered = service.filter_ircc_emails(emails)
        assert len(filtered) == 1

    def test_parse_acknowledgement(self):
        """Parse acknowledgement notification type."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Acknowledgement of Receipt - Application #12345",
                "body_preview": "We have received your application.",
            }
        )
        assert result["notification_type"] == "acknowledgement"

    def test_parse_biometrics(self):
        """Parse biometrics request."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Biometrics Instruction Letter",
                "body_preview": "You are required to provide biometric information.",
            }
        )
        assert result["notification_type"] == "biometrics"
        assert result["action_required"] is not None

    def test_parse_decision(self):
        """Parse decision notification."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Decision Made on Your Application",
                "body_preview": "A decision has been made. Your application has been approved.",
            }
        )
        assert result["notification_type"] == "decision"

    def test_parse_additional_documents(self):
        """Parse request for additional documents."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Request for Additional Documents",
                "body_preview": "Please provide additional documents to support your application.",
            }
        )
        assert result["notification_type"] == "additional_documents"
        assert result["action_required"] is not None

    def test_parse_medical(self):
        """Parse medical exam request."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Upfront Medical Exam Required",
                "body_preview": "You must complete a medical examination.",
            }
        )
        assert result["notification_type"] == "medical"

    def test_parse_passport_request(self):
        """Parse passport request."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Passport Request",
                "body_preview": "Please send your passport for visa stamping.",
            }
        )
        assert result["notification_type"] == "passport_request"

    def test_parse_general_unknown(self):
        """Unknown email type defaults to general."""
        service = EmailService()
        result = service.parse_ircc_email(
            {
                "subject": "Some other email",
                "body_preview": "Random content that doesnt match.",
            }
        )
        assert result["notification_type"] == "general"
        assert result["action_required"] is None

    def test_gmail_auth_url(self):
        """Gmail service generates auth URL."""
        service = GmailService()
        with patch.object(service, "_client_id", "test_id"):
            url = service.get_auth_url("test_state")
            assert "accounts.google.com" in url
            assert "test_id" in url
            assert "test_state" in url

    def test_outlook_auth_url(self):
        """Outlook service generates auth URL."""
        service = OutlookService()
        with patch.object(service, "_client_id", "test_id"):
            url = service.get_auth_url("test_state")
            assert "login.microsoftonline.com" in url
            assert "test_id" in url


# =============================================================================
# Email API Tests
# =============================================================================


class TestEmailAPI:
    """Integration tests for email API endpoints."""

    @pytest.mark.anyio
    async def test_connect_gmail_not_configured(self, client):
        """Gmail connect returns 503 when not configured."""
        async with TestSessionLocal() as session:
            admin = User(
                email="admin2@email.com",
                hashed_password=hash_password("pass"),
                full_name="Admin2",
                role=UserRole.admin,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            token = create_access_token(
                {"sub": str(admin.id), "email": admin.email, "role": "admin"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/email/connect/gmail?candidate_id=1",
            headers=headers,
        )
        assert response.status_code == 503

    @pytest.mark.anyio
    async def test_disconnect_email(self, client):
        """Disconnect revokes email connection."""
        candidate_id, connection_id, headers = await setup_candidate_with_connection()

        response = await client.delete(
            f"/email/disconnect/{connection_id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert "revoquee" in response.json()["message"]

    @pytest.mark.anyio
    async def test_disconnect_not_found(self, client):
        """Disconnect returns 404 for non-existent connection."""
        _, _, headers = await setup_candidate_with_connection()

        response = await client.delete(
            "/email/disconnect/9999",
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_list_connections(self, client):
        """List email connections for a candidate."""
        candidate_id, _, headers = await setup_candidate_with_connection()

        response = await client.get(
            f"/email/candidates/{candidate_id}/connections",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "gmail"
        assert data[0]["email_address"] == "jean.dupont@gmail.com"

    @pytest.mark.anyio
    async def test_list_ircc_emails_empty(self, client):
        """List IRCC emails returns empty when none stored."""
        candidate_id, _, headers = await setup_candidate_with_connection()

        response = await client.get(
            f"/email/candidates/{candidate_id}/emails",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_list_ircc_emails_with_data(self, client):
        """List IRCC emails returns stored emails."""
        candidate_id, connection_id, headers = await setup_candidate_with_connection()

        # Insert an IRCC email directly
        async with TestSessionLocal() as session:
            email = IRCCEmail(
                candidate_id=candidate_id,
                connection_id=connection_id,
                message_id="msg_123",
                sender="noreply@cic.gc.ca",
                subject="Decision on your application",
                body_preview="Your application has been approved.",
                notification_type="decision",
                received_at=datetime.utcnow(),
            )
            session.add(email)
            await session.commit()

        response = await client.get(
            f"/email/candidates/{candidate_id}/emails",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["notification_type"] == "decision"

    @pytest.mark.anyio
    async def test_mark_email_read(self, client):
        """Mark an IRCC email as read."""
        candidate_id, connection_id, headers = await setup_candidate_with_connection()

        async with TestSessionLocal() as session:
            email = IRCCEmail(
                candidate_id=candidate_id,
                connection_id=connection_id,
                message_id="msg_456",
                sender="updates@canada.ca",
                subject="Update",
                notification_type="update",
                received_at=datetime.utcnow(),
                is_read=False,
            )
            session.add(email)
            await session.commit()
            await session.refresh(email)
            email_id = email.id

        response = await client.put(
            f"/email/emails/{email_id}/read",
            headers=headers,
        )
        assert response.status_code == 200
        assert "lu" in response.json()["message"]

    @pytest.mark.anyio
    async def test_mark_email_not_found(self, client):
        """Mark read returns 404 for non-existent email."""
        _, _, headers = await setup_candidate_with_connection()

        response = await client.put(
            "/email/emails/9999/read",
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_sync_no_connections(self, client):
        """Sync returns 404 when no active connections."""
        async with TestSessionLocal() as session:
            admin = User(
                email="admin3@email.com",
                hashed_password=hash_password("pass"),
                full_name="Admin3",
                role=UserRole.admin,
            )
            candidate = Candidate(first_name="No", last_name="Connection", email="no@conn.com")
            session.add_all([admin, candidate])
            await session.commit()
            await session.refresh(admin)
            await session.refresh(candidate)

            token = create_access_token(
                {"sub": str(admin.id), "email": admin.email, "role": "admin"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            f"/email/candidates/{candidate.id}/sync",
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_candidat_cannot_sync(self, client):
        """Candidat cannot trigger email sync."""
        async with TestSessionLocal() as session:
            candidat = User(
                email="candidat@email.com",
                hashed_password=hash_password("pass"),
                full_name="Candidat",
                role=UserRole.candidat,
            )
            session.add(candidat)
            await session.commit()
            await session.refresh(candidat)

            token = create_access_token(
                {"sub": str(candidat.id), "email": candidat.email, "role": "candidat"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/email/candidates/1/sync",
            headers=headers,
        )
        assert response.status_code == 403
