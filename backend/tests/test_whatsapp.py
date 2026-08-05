"""Tests for WhatsApp notification system."""


import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Base, User, UserRole
from app.models.whatsapp_notification import (
    NotificationPreference,
)
from app.services.whatsapp_service import (
    DEFAULT_PREFERENCES,
    NotificationEvent,
    WhatsAppService,
)

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


async def setup_admin_with_prefs(whatsapp_number: str | None = None) -> tuple[int, dict]:
    """Create admin with notification preferences. Return (user_id, headers)."""
    async with TestSessionLocal() as session:
        admin = User(
            email="admin@whatsapp.com",
            hashed_password=hash_password("pass"),
            full_name="Admin WA",
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        if whatsapp_number:
            prefs = NotificationPreference(
                user_id=admin.id,
                whatsapp_number=whatsapp_number,
                is_enabled=True,
                events=DEFAULT_PREFERENCES,
            )
            session.add(prefs)
            await session.commit()

        token = create_access_token(
            {"sub": str(admin.id), "email": admin.email, "role": "admin"}
        )
        headers = {"Authorization": f"Bearer {token}"}
        return admin.id, headers


# =============================================================================
# WhatsAppService Unit Tests
# =============================================================================


class TestWhatsAppService:
    """Unit tests for WhatsAppService."""

    def test_render_template_ircc_email(self):
        """Render IRCC email detected template."""
        service = WhatsAppService()
        msg = service.render_template(
            NotificationEvent.IRCC_EMAIL_DETECTED,
            {
                "candidate_name": "Jean Dupont",
                "notification_type": "decision",
                "subject": "Decision on application",
                "action_required": "Aucune",
            },
        )
        assert "Jean Dupont" in msg
        assert "decision" in msg
        assert "IRCC" in msg

    def test_render_template_document_missing(self):
        """Render document missing template."""
        service = WhatsAppService()
        msg = service.render_template(
            NotificationEvent.DOCUMENT_MISSING,
            {
                "candidate_name": "Marie Tremblay",
                "dossier_ref": "DOS-001",
                "document_name": "Passeport",
                "priority": "haute",
            },
        )
        assert "Marie Tremblay" in msg
        assert "Passeport" in msg

    def test_render_template_deadline(self):
        """Render deadline approaching template."""
        service = WhatsAppService()
        msg = service.render_template(
            NotificationEvent.DEADLINE_APPROACHING,
            {
                "candidate_name": "Test User",
                "dossier_ref": "DOS-002",
                "deadline_date": "2026-08-15",
                "days_remaining": "5",
            },
        )
        assert "5" in msg
        assert "Deadline" in msg or "deadline" in msg.lower()

    def test_render_template_fraud_alert(self):
        """Render fraud alert template."""
        service = WhatsAppService()
        msg = service.render_template(
            NotificationEvent.FRAUD_ALERT,
            {
                "candidate_name": "Suspect User",
                "document_name": "Passport",
                "risk_level": "high",
                "fraud_score": "75",
            },
        )
        assert "fraude" in msg.lower()
        assert "75" in msg

    def test_render_template_unknown_event(self):
        """Unknown event type falls back to generic message."""
        service = WhatsAppService()
        msg = service.render_template("unknown_event", {"key": "value"})
        assert "unknown_event" in msg

    def test_render_template_missing_keys(self):
        """Missing keys should use placeholder instead of crashing."""
        service = WhatsAppService()
        msg = service.render_template(
            NotificationEvent.IRCC_EMAIL_DETECTED,
            {"candidate_name": "Test"},  # Missing other keys
        )
        assert "Test" in msg
        # Should not crash, placeholders used

    def test_is_configured_false(self):
        """Service not configured without credentials."""
        service = WhatsAppService()
        # In test env, Twilio creds are empty
        assert service.is_configured is False

    @pytest.mark.anyio
    async def test_send_not_configured(self):
        """Send returns not_configured when Twilio not set up."""
        service = WhatsAppService()
        result = await service.send_whatsapp("+15551234567", "Test message")
        assert result["status"] == "not_configured"

    @pytest.mark.anyio
    async def test_notify_event_disabled(self):
        """Notify skips when event is disabled in preferences."""
        service = WhatsAppService()
        result = await service.notify(
            event=NotificationEvent.DOSSIER_STATUS_CHANGE,
            to_number="+15551234567",
            data={"candidate_name": "Test"},
            preferences={NotificationEvent.DOSSIER_STATUS_CHANGE: False},
        )
        assert result["status"] == "skipped"

    @pytest.mark.anyio
    async def test_notify_event_enabled(self):
        """Notify proceeds when event is enabled."""
        service = WhatsAppService()
        result = await service.notify(
            event=NotificationEvent.FRAUD_ALERT,
            to_number="+15551234567",
            data={
                "candidate_name": "Test",
                "document_name": "Passport",
                "risk_level": "high",
                "fraud_score": "80",
            },
            preferences={NotificationEvent.FRAUD_ALERT: True},
        )
        # Will be not_configured in test env
        assert result["status"] in ("not_configured", "sent", "failed")

    def test_default_preferences(self):
        """Default preferences should have expected structure."""
        assert DEFAULT_PREFERENCES[NotificationEvent.IRCC_EMAIL_DETECTED] is True
        assert DEFAULT_PREFERENCES[NotificationEvent.FRAUD_ALERT] is True
        assert DEFAULT_PREFERENCES[NotificationEvent.DOSSIER_STATUS_CHANGE] is False


# =============================================================================
# Notifications API Tests
# =============================================================================


class TestNotificationsAPI:
    """Integration tests for notifications API."""

    @pytest.mark.anyio
    async def test_get_preferences_default(self, client):
        """Get preferences returns defaults when none set."""
        _, headers = await setup_admin_with_prefs()

        response = await client.get("/notifications/preferences", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        assert data["whatsapp_number"] is None
        assert "ircc_email_detected" in data["events"]

    @pytest.mark.anyio
    async def test_update_preferences(self, client):
        """Update notification preferences."""
        _, headers = await setup_admin_with_prefs()

        response = await client.put(
            "/notifications/preferences",
            headers=headers,
            json={
                "whatsapp_number": "+15551234567",
                "is_enabled": True,
                "events": {
                    "ircc_email_detected": True,
                    "fraud_alert": False,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["whatsapp_number"] == "+15551234567"
        assert data["events"]["fraud_alert"] is False

    @pytest.mark.anyio
    async def test_get_preferences_after_update(self, client):
        """Preferences persist after update."""
        _, headers = await setup_admin_with_prefs("+15559876543")

        response = await client.get("/notifications/preferences", headers=headers)
        assert response.status_code == 200
        assert response.json()["whatsapp_number"] == "+15559876543"

    @pytest.mark.anyio
    async def test_send_notification(self, client):
        """Send notification stores in history."""
        _, headers = await setup_admin_with_prefs("+15551234567")

        response = await client.post(
            "/notifications/send",
            headers=headers,
            json={
                "event": NotificationEvent.IRCC_EMAIL_DETECTED,
                "to_number": "+15551234567",
                "data": {
                    "candidate_name": "Jean Dupont",
                    "notification_type": "decision",
                    "subject": "Test",
                    "action_required": "None",
                },
            },
        )
        assert response.status_code == 200
        # Will be not_configured in test env
        assert "status" in response.json()

    @pytest.mark.anyio
    async def test_notification_history(self, client):
        """History endpoint returns stored notifications."""
        _, headers = await setup_admin_with_prefs("+15551234567")

        # Send one first
        await client.post(
            "/notifications/send",
            headers=headers,
            json={
                "event": "test_event",
                "to_number": "+15551234567",
                "data": {"candidate_name": "Test"},
            },
        )

        response = await client.get("/notifications/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.anyio
    async def test_notification_stats(self, client):
        """Stats endpoint returns counts."""
        _, headers = await setup_admin_with_prefs()

        response = await client.get("/notifications/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "sent" in data
        assert "success_rate" in data

    @pytest.mark.anyio
    async def test_test_notification_no_number(self, client):
        """Test notification fails without configured number."""
        _, headers = await setup_admin_with_prefs()  # No number

        response = await client.post("/notifications/test", headers=headers)
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_test_notification_with_number(self, client):
        """Test notification proceeds with configured number."""
        _, headers = await setup_admin_with_prefs("+15551234567")

        response = await client.post("/notifications/test", headers=headers)
        assert response.status_code == 200
        assert "status" in response.json()

    @pytest.mark.anyio
    async def test_candidat_cannot_access(self, client):
        """Candidat cannot access notification endpoints."""
        async with TestSessionLocal() as session:
            candidat = User(
                email="candidat@wa.com",
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

        response = await client.get("/notifications/preferences", headers=headers)
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_consultant_can_view_preferences(self, client):
        """Consultant can view/update preferences."""
        async with TestSessionLocal() as session:
            consultant = User(
                email="consultant@wa.com",
                hashed_password=hash_password("pass"),
                full_name="Consultant",
                role=UserRole.consultant,
            )
            session.add(consultant)
            await session.commit()
            await session.refresh(consultant)

            token = create_access_token(
                {"sub": str(consultant.id), "email": consultant.email, "role": "consultant"}
            )
            headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/notifications/preferences", headers=headers)
        assert response.status_code == 200
