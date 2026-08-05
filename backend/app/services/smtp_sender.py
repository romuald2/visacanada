"""Outbound email delivery over SMTP.

Separate from `email_service.py`, which reads *incoming* IRCC mail via the Gmail
and Microsoft Graph APIs. This module only sends.

Degrades the same way the WhatsApp sender does: when SMTP is not configured the
service reports `not_configured` instead of raising, so alert delivery still
records its dashboard notifications and never fails a scheduled scan because
mail is unavailable.

Privacy: bodies routinely carry candidate names and dossier references, so
nothing beyond the recipient count and a status is ever logged.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

import anyio

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMTPSender:
    """Sends transactional email through a configured SMTP relay."""

    def __init__(self) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._username = settings.smtp_username
        self._password = settings.smtp_password
        self._from = settings.smtp_from or settings.smtp_username
        self._use_tls = settings.smtp_use_tls
        self._timeout = settings.smtp_timeout_seconds

    @property
    def is_configured(self) -> bool:
        """True when a relay host and a sender address are both available."""
        return bool(self._host and self._from)

    def _build_message(self, to: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        return message

    def _send_blocking(self, message: EmailMessage) -> None:
        """Synchronous SMTP dialogue, run off the event loop by `send`."""
        if self._use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
                client.starttls(context=context)
                if self._username:
                    client.login(self._username, self._password)
                client.send_message(message)
        else:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
                if self._username:
                    client.login(self._username, self._password)
                client.send_message(message)

    async def send(self, to: str, subject: str, body: str) -> dict[str, str]:
        """Send one message. Returns a status dict, never raises on failure.

        Callers treat delivery as best-effort: a relay outage must not abort a
        scan or an API request, so transport errors are reported rather than
        propagated.
        """
        if not self.is_configured:
            return {"status": "not_configured", "error": "SMTP non configure"}
        if not to:
            return {"status": "failed", "error": "Destinataire manquant"}

        message = self._build_message(to, subject, body)
        try:
            # smtplib is blocking; keep it off the event loop.
            await anyio.to_thread.run_sync(self._send_blocking, message)
        except Exception as exc:
            # Log the error type only — the message body and the recipient
            # address are personal data.
            logger.warning("Echec envoi SMTP (%s)", type(exc).__name__)
            return {"status": "failed", "error": type(exc).__name__}
        return {"status": "sent"}


# Singleton
smtp_sender = SMTPSender()
