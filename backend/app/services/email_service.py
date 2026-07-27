"""Email Integration Service.

Connects to Gmail (Google API) and Outlook (Microsoft Graph) via OAuth2.
Filters and parses IRCC emails from @cic.gc.ca and @canada.ca domains.
Manages consent, token refresh, and email sync.
"""

import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings


# IRCC sender domains
IRCC_DOMAINS = ["@cic.gc.ca", "@canada.ca", "@ircc-cisr.gc.ca"]

# IRCC notification type keywords
IRCC_NOTIFICATION_TYPES = {
    "acknowledgement": ["acknowledgement", "accuse de reception", "we have received"],
    "biometrics": ["biometrics", "biometriques", "biometric"],
    "medical": ["medical", "medicale", "upfront medical"],
    "additional_documents": ["additional documents", "documents supplementaires", "please provide"],
    "decision": ["approved", "refused", "decision", "approuve", "refuse"],
    "passport_request": ["passport", "passeport", "original documents"],
    "interview": ["interview", "entrevue", "hearing"],
    "update": ["update", "mise a jour", "status change"],
}


class EmailService:
    """Base class for email provider integration."""

    def filter_ircc_emails(self, emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter emails from IRCC domains only."""
        ircc_emails = []
        for email in emails:
            sender = (email.get("sender") or email.get("from", "")).lower()
            if any(domain in sender for domain in IRCC_DOMAINS):
                ircc_emails.append(email)
        return ircc_emails

    def parse_ircc_email(self, email: dict[str, Any]) -> dict[str, Any]:
        """Parse an IRCC email to determine notification type and action."""
        subject = (email.get("subject") or "").lower()
        body = (email.get("body_preview") or email.get("body") or "").lower()
        content = f"{subject} {body}"

        notification_type = "general"
        for ntype, keywords in IRCC_NOTIFICATION_TYPES.items():
            if any(kw in content for kw in keywords):
                notification_type = ntype
                break

        # Detect action required
        action_required = None
        action_patterns = [
            (r"please (submit|provide|send|upload)", "Fournir des documents supplementaires"),
            (r"(documents supplementaires|additional documents)", "Documents requis"),
            (r"(biometric|biometriques)", "Prendre rendez-vous biometrie"),
            (r"(medical exam|examen medical)", "Passer examen medical"),
            (r"(interview|entrevue)", "Preparer entrevue"),
            (r"(passport|passeport).*(send|envoyer)", "Envoyer passeport"),
        ]

        for pattern, action in action_patterns:
            if re.search(pattern, content):
                action_required = action
                break

        return {
            "notification_type": notification_type,
            "action_required": action_required,
        }


class GmailService(EmailService):
    """Gmail integration via Google API."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://gmail.googleapis.com/gmail/v1"
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self):
        self._client_id = settings.google_client_id
        self._client_secret = settings.google_client_secret
        self._redirect_uri = settings.google_redirect_uri

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def get_auth_url(self, state: str) -> str:
        """Generate OAuth2 authorization URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                },
            )
            if response.status_code != 200:
                raise ValueError(f"Gmail token exchange failed: {response.text}")
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if response.status_code != 200:
                raise ValueError(f"Gmail token refresh failed: {response.text}")
            return response.json()

    async def get_user_email(self, access_token: str) -> str:
        """Get the authenticated user's email address."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/users/me/profile",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                raise ValueError("Failed to get Gmail profile")
            return response.json().get("emailAddress", "")

    async def fetch_ircc_emails(
        self, access_token: str, after_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Fetch emails from IRCC domains."""
        # Build Gmail search query for IRCC domains
        query_parts = [f"from:{domain}" for domain in IRCC_DOMAINS]
        query = " OR ".join(query_parts)
        if after_date:
            query += f" after:{after_date.strftime('%Y/%m/%d')}"

        async with httpx.AsyncClient() as client:
            # List messages
            response = await client.get(
                f"{self.API_BASE}/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": query, "maxResults": 50},
            )
            if response.status_code != 200:
                return []

            messages = response.json().get("messages", [])
            emails = []

            for msg in messages[:20]:  # Limit to 20 per sync
                detail = await client.get(
                    f"{self.API_BASE}/users/me/messages/{msg['id']}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                )
                if detail.status_code == 200:
                    msg_data = detail.json()
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in msg_data.get("payload", {}).get("headers", [])
                    }
                    emails.append({
                        "message_id": msg["id"],
                        "sender": headers.get("from", ""),
                        "subject": headers.get("subject", ""),
                        "body_preview": msg_data.get("snippet", ""),
                        "received_at": headers.get("date", ""),
                    })

        return self.filter_ircc_emails(emails)


class OutlookService(EmailService):
    """Outlook/Microsoft 365 integration via Microsoft Graph."""

    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    API_BASE = "https://graph.microsoft.com/v1.0"
    SCOPES = ["Mail.Read", "User.Read", "offline_access"]

    def __init__(self):
        self._client_id = settings.microsoft_client_id
        self._client_secret = settings.microsoft_client_secret
        self._redirect_uri = settings.microsoft_redirect_uri

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def get_auth_url(self, state: str) -> str:
        """Generate OAuth2 authorization URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                    "scope": " ".join(self.SCOPES),
                },
            )
            if response.status_code != 200:
                raise ValueError(f"Outlook token exchange failed: {response.text}")
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": " ".join(self.SCOPES),
                },
            )
            if response.status_code != 200:
                raise ValueError(f"Outlook token refresh failed: {response.text}")
            return response.json()

    async def get_user_email(self, access_token: str) -> str:
        """Get the authenticated user's email address."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                raise ValueError("Failed to get Outlook profile")
            return response.json().get("mail", "") or response.json().get("userPrincipalName", "")

    async def fetch_ircc_emails(
        self, access_token: str, after_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Fetch emails from IRCC domains via Microsoft Graph."""
        # Build OData filter for IRCC senders
        filters = []
        for domain in IRCC_DOMAINS:
            filters.append(f"contains(from/emailAddress/address, '{domain.lstrip('@')}')")
        filter_str = " or ".join(filters)

        if after_date:
            filter_str = f"({filter_str}) and receivedDateTime ge {after_date.isoformat()}Z"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "$filter": filter_str,
                    "$top": 20,
                    "$select": "id,from,subject,bodyPreview,receivedDateTime",
                    "$orderby": "receivedDateTime desc",
                },
            )
            if response.status_code != 200:
                return []

            messages = response.json().get("value", [])
            emails = []

            for msg in messages:
                from_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
                emails.append({
                    "message_id": msg["id"],
                    "sender": from_addr,
                    "subject": msg.get("subject", ""),
                    "body_preview": msg.get("bodyPreview", ""),
                    "received_at": msg.get("receivedDateTime", ""),
                })

        return self.filter_ircc_emails(emails)


# Singletons
gmail_service = GmailService()
outlook_service = OutlookService()
