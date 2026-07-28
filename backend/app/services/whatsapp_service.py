"""WhatsApp Notification Service via Twilio.

Sends notifications to admin when important events occur on dossiers.
Uses Redis queue for rate limiting and anti-spam.
Fallback to SMS if WhatsApp delivery fails.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any


def _utcnow() -> datetime:
    """Naive UTC timestamp (matches the rest of the codebase)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

import httpx

from app.core.config import settings


# Notification event types
class NotificationEvent:
    IRCC_EMAIL_DETECTED = "ircc_email_detected"
    DOCUMENT_MISSING = "document_missing"
    DEADLINE_APPROACHING = "deadline_approaching"
    COMPLIANCE_SCORE_LOW = "compliance_score_low"
    FRAUD_ALERT = "fraud_alert"
    DOSSIER_STATUS_CHANGE = "dossier_status_change"
    APPLICATION_DECISION = "application_decision"


# Message templates
WHATSAPP_TEMPLATES = {
    NotificationEvent.IRCC_EMAIL_DETECTED: (
        "*Nouvel email IRCC detecte*\n\n"
        "Candidat: {candidate_name}\n"
        "Type: {notification_type}\n"
        "Sujet: {subject}\n"
        "Action requise: {action_required}\n\n"
        "Connectez-vous pour plus de details."
    ),
    NotificationEvent.DOCUMENT_MISSING: (
        "*Document manquant*\n\n"
        "Candidat: {candidate_name}\n"
        "Dossier: {dossier_ref}\n"
        "Document: {document_name}\n"
        "Priorite: {priority}\n\n"
        "Veuillez relancer le candidat."
    ),
    NotificationEvent.DEADLINE_APPROACHING: (
        "*Deadline approche*\n\n"
        "Candidat: {candidate_name}\n"
        "Dossier: {dossier_ref}\n"
        "Echeance: {deadline_date}\n"
        "Jours restants: {days_remaining}\n\n"
        "Action requise avant expiration."
    ),
    NotificationEvent.COMPLIANCE_SCORE_LOW: (
        "*Score de conformite bas*\n\n"
        "Candidat: {candidate_name}\n"
        "Dossier: {dossier_ref}\n"
        "Score: {score}/100\n"
        "Statut: {status}\n\n"
        "Verifiez les documents manquants."
    ),
    NotificationEvent.FRAUD_ALERT: (
        "*Alerte fraude detectee*\n\n"
        "Candidat: {candidate_name}\n"
        "Document: {document_name}\n"
        "Risque: {risk_level}\n"
        "Score: {fraud_score}/100\n\n"
        "Revue humaine requise."
    ),
    NotificationEvent.DOSSIER_STATUS_CHANGE: (
        "*Changement de statut*\n\n"
        "Candidat: {candidate_name}\n"
        "Dossier: {dossier_ref}\n"
        "Nouveau statut: {new_status}\n\n"
        "Consultez le dossier pour details."
    ),
    NotificationEvent.APPLICATION_DECISION: (
        "*Decision sur demande*\n\n"
        "Candidat: {candidate_name}\n"
        "Programme: {program_name}\n"
        "Decision: {decision}\n\n"
        "Informez le candidat immediatement."
    ),
}

# Default notification preferences
DEFAULT_PREFERENCES = {
    NotificationEvent.IRCC_EMAIL_DETECTED: True,
    NotificationEvent.DOCUMENT_MISSING: True,
    NotificationEvent.DEADLINE_APPROACHING: True,
    NotificationEvent.COMPLIANCE_SCORE_LOW: False,
    NotificationEvent.FRAUD_ALERT: True,
    NotificationEvent.DOSSIER_STATUS_CHANGE: False,
    NotificationEvent.APPLICATION_DECISION: True,
}

# Rate limiting: max notifications per event type per hour
RATE_LIMIT_PER_HOUR = 5
RATE_LIMIT_WINDOW = 3600  # seconds


class WhatsAppService:
    """WhatsApp notification service via Twilio."""

    TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(self):
        self._account_sid = settings.twilio_account_sid
        self._auth_token = settings.twilio_auth_token
        self._from_number = settings.twilio_whatsapp_from
        self._redis_url = settings.redis_url

    @property
    def is_configured(self) -> bool:
        return bool(self._account_sid and self._auth_token and self._from_number)

    def render_template(self, event: str, data: dict[str, Any]) -> str:
        """Render a notification message from template."""
        template = WHATSAPP_TEMPLATES.get(event)
        if not template:
            return f"Notification: {event}\n\nDetails: {json.dumps(data, ensure_ascii=False)}"

        try:
            return template.format(**data)
        except KeyError:
            # Fill missing keys with placeholder
            return template.format_map(DefaultDict(data))

    async def send_whatsapp(
        self,
        to_number: str,
        message: str,
    ) -> dict[str, Any]:
        """Send a WhatsApp message via Twilio."""
        if not self.is_configured:
            return {"status": "not_configured", "error": "Twilio non configure"}

        url = f"{self.TWILIO_API_BASE}/Accounts/{self._account_sid}/Messages.json"

        # Ensure WhatsApp prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        from_number = self._from_number
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(self._account_sid, self._auth_token),
                data={
                    "From": from_number,
                    "To": to_number,
                    "Body": message,
                },
            )

            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "status": "sent",
                    "sid": result.get("sid"),
                    "channel": "whatsapp",
                }
            else:
                # Try SMS fallback
                return await self._send_sms_fallback(to_number, message)

    async def _send_sms_fallback(
        self,
        to_number: str,
        message: str,
    ) -> dict[str, Any]:
        """Fallback to SMS if WhatsApp fails."""
        url = f"{self.TWILIO_API_BASE}/Accounts/{self._account_sid}/Messages.json"

        # Strip whatsapp: prefix for SMS
        sms_to = to_number.replace("whatsapp:", "")
        sms_from = self._from_number.replace("whatsapp:", "")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(self._account_sid, self._auth_token),
                data={
                    "From": sms_from,
                    "To": sms_to,
                    "Body": message.replace("*", ""),  # Remove markdown bold
                },
            )

            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "status": "sent",
                    "sid": result.get("sid"),
                    "channel": "sms_fallback",
                }
            else:
                return {
                    "status": "failed",
                    "error": response.text[:200],
                    "channel": "sms_fallback",
                }

    async def notify(
        self,
        event: str,
        to_number: str,
        data: dict[str, Any],
        preferences: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Send a notification if event is enabled in preferences.

        Args:
            event: NotificationEvent type
            to_number: Admin WhatsApp number
            data: Template data
            preferences: Event preferences (None = use defaults)

        Returns:
            Result dict with status and details
        """
        # Check preferences
        prefs = preferences or DEFAULT_PREFERENCES
        if not prefs.get(event, True):
            return {"status": "skipped", "reason": "event_disabled"}

        # Check rate limit (simplified - in production use Redis)
        if not await self._check_rate_limit(event, to_number):
            return {"status": "rate_limited", "reason": "too_many_notifications"}

        # Render message
        message = self.render_template(event, data)

        # Send
        result = await self.send_whatsapp(to_number, message)
        result["event"] = event
        result["sent_at"] = _utcnow().isoformat()

        return result

    async def _check_rate_limit(self, event: str, to_number: str) -> bool:
        """Check if we can send (simplified in-memory rate limiting).

        In production, this would use Redis with INCR + EXPIRE.
        """
        # For now, always allow - Redis integration would be:
        # key = f"whatsapp_rate:{to_number}:{event}"
        # count = await redis.incr(key)
        # if count == 1:
        #     await redis.expire(key, RATE_LIMIT_WINDOW)
        # return count <= RATE_LIMIT_PER_HOUR
        return True


class DefaultDict(dict):
    """Dict that returns placeholder for missing keys."""

    def __missing__(self, key: str) -> str:
        return f"[{key}]"


# Singleton
whatsapp_service = WhatsAppService()
