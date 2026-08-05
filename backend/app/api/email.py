"""Email integration API router."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.email_connection import EmailConnection, EmailProvider, IRCCEmail
from app.models.user import User, UserRole
from app.services.email_service import gmail_service, outlook_service

router = APIRouter(prefix="/email", tags=["email"])


def _utcnow() -> datetime:
    """Naive UTC timestamp (matches the rest of the codebase)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/connect/gmail")
async def connect_gmail(
    candidate_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Initiate Gmail OAuth2 connection for a candidate."""
    if not gmail_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration non configuree",
        )
    state = f"gmail:{candidate_id}:{secrets.token_urlsafe(16)}"
    auth_url = gmail_service.get_auth_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/connect/outlook")
async def connect_outlook(
    candidate_id: int,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Initiate Outlook OAuth2 connection for a candidate."""
    if not outlook_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outlook integration non configuree",
        )
    state = f"outlook:{candidate_id}:{secrets.token_urlsafe(16)}"
    auth_url = outlook_service.get_auth_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/callback/gmail")
async def gmail_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Gmail OAuth2 callback."""
    parts = state.split(":")
    if len(parts) < 2 or parts[0] != "gmail":
        raise HTTPException(status_code=400, detail="State invalide")

    candidate_id = int(parts[1])

    try:
        token_data = await gmail_service.exchange_code(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    email_address = await gmail_service.get_user_email(access_token)

    connection = EmailConnection(
        candidate_id=candidate_id,
        provider=EmailProvider.gmail,
        email_address=email_address,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=_utcnow() + timedelta(seconds=expires_in),
        is_active=True,
    )
    db.add(connection)
    await db.commit()

    return {"message": "Connexion Gmail reussie", "email": email_address}


@router.get("/callback/outlook")
async def outlook_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Outlook OAuth2 callback."""
    parts = state.split(":")
    if len(parts) < 2 or parts[0] != "outlook":
        raise HTTPException(status_code=400, detail="State invalide")

    candidate_id = int(parts[1])

    try:
        token_data = await outlook_service.exchange_code(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    email_address = await outlook_service.get_user_email(access_token)

    connection = EmailConnection(
        candidate_id=candidate_id,
        provider=EmailProvider.outlook,
        email_address=email_address,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=_utcnow() + timedelta(seconds=expires_in),
        is_active=True,
    )
    db.add(connection)
    await db.commit()

    return {"message": "Connexion Outlook reussie", "email": email_address}


# PLACEHOLDER_REMAINING


@router.delete("/disconnect/{connection_id}")
async def disconnect_email(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Revoke consent and disconnect email integration."""
    result = await db.execute(
        select(EmailConnection).where(EmailConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connexion non trouvee")

    connection.is_active = False
    connection.consent_revoked_at = _utcnow()
    await db.commit()

    return {"message": "Connexion email revoquee"}


@router.get("/candidates/{candidate_id}/connections")
async def list_email_connections(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List email connections for a candidate."""
    result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.candidate_id == candidate_id,
            EmailConnection.is_active == True,  # noqa: E712
        )
    )
    connections = result.scalars().all()

    return [
        {
            "id": c.id,
            "provider": c.provider.value,
            "email_address": c.email_address,
            "is_active": c.is_active,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "consent_given_at": c.consent_given_at.isoformat(),
        }
        for c in connections
    ]


@router.post("/candidates/{candidate_id}/sync")
async def sync_candidate_emails(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Manually sync IRCC emails for a candidate."""
    result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.candidate_id == candidate_id,
            EmailConnection.is_active == True,  # noqa: E712
        )
    )
    connections = result.scalars().all()

    if not connections:
        raise HTTPException(
            status_code=404,
            detail="Aucune connexion email active pour ce candidat",
        )

    total_new = 0

    for conn in connections:
        # Refresh token if expired
        if conn.token_expires_at and conn.token_expires_at < _utcnow():
            if not conn.refresh_token:
                continue
            try:
                if conn.provider == EmailProvider.gmail:
                    token_data = await gmail_service.refresh_access_token(conn.refresh_token)
                else:
                    token_data = await outlook_service.refresh_access_token(conn.refresh_token)
                conn.access_token = token_data["access_token"]
                conn.token_expires_at = _utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
            except ValueError:
                continue

        # Fetch IRCC emails
        try:
            if conn.provider == EmailProvider.gmail:
                emails = await gmail_service.fetch_ircc_emails(
                    conn.access_token, after_date=conn.last_sync_at
                )
            else:
                emails = await outlook_service.fetch_ircc_emails(
                    conn.access_token, after_date=conn.last_sync_at
                )
        except Exception:
            continue

        # Store new emails (deduplicate)
        for email_data in emails:
            existing = await db.execute(
                select(IRCCEmail).where(IRCCEmail.message_id == email_data["message_id"])
            )
            if existing.scalar_one_or_none():
                continue

            svc = gmail_service if conn.provider == EmailProvider.gmail else outlook_service
            parsed = svc.parse_ircc_email(email_data)

            received_at = _utcnow()
            if email_data.get("received_at"):
                try:
                    received_at = datetime.fromisoformat(
                        str(email_data["received_at"]).replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            ircc_email = IRCCEmail(
                candidate_id=candidate_id,
                connection_id=conn.id,
                message_id=email_data["message_id"],
                sender=email_data["sender"],
                subject=email_data["subject"],
                body_preview=email_data.get("body_preview"),
                notification_type=parsed["notification_type"],
                action_required=parsed["action_required"],
                received_at=received_at,
            )
            db.add(ircc_email)
            total_new += 1

        conn.last_sync_at = _utcnow()

    await db.commit()
    return {"message": f"{total_new} nouveau(x) email(s) IRCC detecte(s)", "new_emails": total_new}


# PLACEHOLDER_LIST_EMAILS


@router.get("/candidates/{candidate_id}/emails")
async def list_ircc_emails(
    candidate_id: int,
    is_read: bool | None = None,
    notification_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List detected IRCC emails for a candidate."""
    if current_user.role == UserRole.candidat:
        result = await db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.user_id == current_user.id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Acces refuse")

    query = select(IRCCEmail).where(IRCCEmail.candidate_id == candidate_id)

    if is_read is not None:
        query = query.where(IRCCEmail.is_read == is_read)
    if notification_type:
        query = query.where(IRCCEmail.notification_type == notification_type)

    query = query.order_by(IRCCEmail.received_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    emails = result.scalars().all()

    return [
        {
            "id": e.id,
            "sender": e.sender,
            "subject": e.subject,
            "body_preview": e.body_preview,
            "notification_type": e.notification_type,
            "action_required": e.action_required,
            "is_read": e.is_read,
            "received_at": e.received_at.isoformat(),
            "dossier_id": e.dossier_id,
        }
        for e in emails
    ]


@router.put("/emails/{email_id}/read")
async def mark_email_read(
    email_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an IRCC email as read."""
    result = await db.execute(
        select(IRCCEmail).where(IRCCEmail.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trouve")

    email.is_read = True
    await db.commit()

    return {"message": "Email marque comme lu"}
