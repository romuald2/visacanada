"""Tests for the outbound SMTP sender.

No real relay is contacted: `_send_blocking` is replaced so the tests pin down
the contract callers rely on — a status dict, never an exception, and no
personal data in logs.
"""

from email.message import EmailMessage

from app.services.smtp_sender import SMTPSender


def _sender(**overrides) -> SMTPSender:
    """Build a sender with an in-test configuration, bypassing settings."""
    sender = SMTPSender()
    sender._host = overrides.get("host", "smtp.example.test")
    sender._port = overrides.get("port", 587)
    sender._username = overrides.get("username", "user")
    sender._password = overrides.get("password", "secret")
    sender._from = overrides.get("sender_from", "no-reply@example.test")
    sender._use_tls = overrides.get("use_tls", True)
    sender._timeout = overrides.get("timeout", 10)
    return sender


class TestConfiguration:
    def test_not_configured_without_host(self):
        assert _sender(host="").is_configured is False

    def test_not_configured_without_from_address(self):
        assert _sender(sender_from="").is_configured is False

    def test_configured_with_host_and_from(self):
        assert _sender().is_configured is True

    async def test_send_reports_not_configured_instead_of_raising(self):
        result = await _sender(host="").send("a@example.test", "sujet", "corps")
        assert result == {"status": "not_configured", "error": "SMTP non configure"}

    async def test_send_does_not_touch_the_relay_when_unconfigured(self):
        sender = _sender(host="")
        called = False

        def _fail(_message):
            nonlocal called
            called = True

        sender._send_blocking = _fail
        await sender.send("a@example.test", "sujet", "corps")
        assert called is False


class TestMessageBuilding:
    def test_headers_and_body(self):
        message = _sender()._build_message("dest@example.test", "Sujet", "Corps")
        assert message["From"] == "no-reply@example.test"
        assert message["To"] == "dest@example.test"
        assert message["Subject"] == "Sujet"
        assert message.get_content().strip() == "Corps"

    def test_accented_subject_and_body_survive(self):
        message = _sender()._build_message(
            "dest@example.test", "Échéance dépassée", "Solde à régler : 250,00 $"
        )
        assert message["Subject"] == "Échéance dépassée"
        assert "à régler" in message.get_content()


class TestSending:
    async def test_successful_send_reports_sent(self):
        sender = _sender()
        captured: list[EmailMessage] = []
        sender._send_blocking = captured.append

        result = await sender.send("dest@example.test", "Sujet", "Corps")

        assert result == {"status": "sent"}
        assert len(captured) == 1
        assert captured[0]["To"] == "dest@example.test"

    async def test_missing_recipient_is_rejected_before_connecting(self):
        sender = _sender()
        called = False

        def _fail(_message):
            nonlocal called
            called = True

        sender._send_blocking = _fail
        result = await sender.send("", "Sujet", "Corps")

        assert result["status"] == "failed"
        assert called is False

    async def test_transport_error_is_reported_not_raised(self):
        sender = _sender()

        def _boom(_message):
            raise ConnectionRefusedError("relay down")

        sender._send_blocking = _boom
        result = await sender.send("dest@example.test", "Sujet", "Corps")

        assert result == {"status": "failed", "error": "ConnectionRefusedError"}

    async def test_failure_log_carries_no_recipient_or_body(self, caplog):
        sender = _sender()

        def _boom(_message):
            raise TimeoutError("slow relay")

        sender._send_blocking = _boom
        with caplog.at_level("WARNING"):
            await sender.send("candidat@example.test", "Sujet", "Corps confidentiel")

        logged = caplog.text
        # Subjects and bodies routinely carry candidate names and dossier data.
        assert "candidat@example.test" not in logged
        assert "Corps confidentiel" not in logged
        assert "TimeoutError" in logged
