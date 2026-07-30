"""Intelligent alert engine.

Scans dossiers/documents for proactive conditions and produces Alert records:
- passport expiring within 6 months
- medical exam expiring soon
- language results expiring soon
- new Express Entry round with a compatible score
- IRCC policy change impacting a dossier
- submission deadline approaching

Alerts are deduplicated per (dossier, type, period) via a dedup_key so repeated
scans do not create duplicates. Delivery across channels (dashboard/email/whatsapp)
is driven by each dossier's AlertConfig.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import (
    Alert,
    AlertConfig,
    AlertSeverity,
    AlertType,
)
from app.models.deadline import Deadline, DeadlineType
from app.models.document import Document, DocumentType
from app.models.dossier import Dossier, DossierStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from app.models.user import User, UserRole
from app.services.smtp_sender import smtp_sender
from app.services.whatsapp_service import NotificationEvent, whatsapp_service

# Thresholds (days)
PASSPORT_EXPIRY_DAYS = 180  # 6 months
MEDICAL_EXPIRY_DAYS = 60
LANGUAGE_EXPIRY_DAYS = 90
SUBMISSION_DEADLINE_DAYS = 30

# Default channel toggles when a dossier has no AlertConfig.channels set.
DEFAULT_CHANNELS = {"dashboard": True, "email": True, "whatsapp": False}

# Per-deadline-type: the AlertType to emit, the window (days) within which
# an approaching deadline starts alerting, and the label used in messages.
DEADLINE_RULES: dict[DeadlineType, tuple[AlertType, int, str]] = {
    DeadlineType.ita_response: (AlertType.ita_response, 60, "Reponse a l'invitation (ITA)"),
    DeadlineType.biometrics: (AlertType.biometrics, 30, "Collecte des biometries"),
    DeadlineType.ppr: (AlertType.ppr, 30, "Demande de passeport (PPR)"),
    DeadlineType.medical_request: (AlertType.medical_request, 30, "Examen medical demande"),
    DeadlineType.submission: (AlertType.submission_deadline, 30, "Soumission du dossier"),
    DeadlineType.work_permit_expiry: (AlertType.permit_expiring, 90, "Permis de travail"),
    DeadlineType.study_permit_expiry: (AlertType.permit_expiring, 90, "Permis d'etudes"),
    DeadlineType.custom: (AlertType.submission_deadline, 30, "Echeance"),
}


def _naive(dt: datetime | None) -> datetime | None:
    """Normalize to naive UTC for comparison with SQLite-stored datetimes."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class AlertService:
    """Detects alert conditions and persists deduplicated Alert records."""

    def __init__(self):
        self._now = None

    def _now_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    async def _config_for(
        self, dossier_id: int, db: AsyncSession
    ) -> AlertConfig | None:
        result = await db.execute(
            select(AlertConfig).where(AlertConfig.dossier_id == dossier_id)
        )
        return result.scalar_one_or_none()

    def _type_enabled(self, config: AlertConfig | None, alert_type: AlertType) -> bool:
        if config is None:
            return True
        if not config.is_enabled:
            return False
        enabled = config.enabled_types or {}
        # Default enabled unless explicitly turned off
        return enabled.get(alert_type.value, True)

    async def _emit(
        self,
        db: AsyncSession,
        dossier_id: int,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        dedup_key: str,
        extra_data: dict[str, Any] | None = None,
    ) -> Alert | None:
        """Create an alert if one with the same dedup_key doesn't already exist."""
        existing = await db.execute(
            select(Alert).where(Alert.dedup_key == dedup_key)
        )
        if existing.scalar_one_or_none() is not None:
            return None

        alert = Alert(
            dossier_id=dossier_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            dedup_key=dedup_key,
            extra_data=extra_data,
        )
        db.add(alert)
        return alert


    async def scan_document_expiries(
        self, db: AsyncSession, dossier: Dossier, config: AlertConfig | None
    ) -> list[Alert]:
        """Check passport / medical / language document expiries for a dossier."""
        now = self._now_naive()
        created: list[Alert] = []

        doc_result = await db.execute(
            select(Document).where(Document.dossier_id == dossier.id)
        )
        documents = doc_result.scalars().all()

        # Map document type -> alert type + threshold + label
        checks = {
            DocumentType.passport: (
                AlertType.passport_expiring,
                PASSPORT_EXPIRY_DAYS,
                "Passeport",
            ),
            DocumentType.medical_exam: (
                AlertType.medical_expiring,
                MEDICAL_EXPIRY_DAYS,
                "Examen medical",
            ),
            DocumentType.language_test: (
                AlertType.language_expiring,
                LANGUAGE_EXPIRY_DAYS,
                "Test de langue",
            ),
        }

        for doc in documents:
            if doc.document_type not in checks:
                continue
            if doc.expires_at is None:
                continue

            alert_type, threshold, label = checks[doc.document_type]
            if not self._type_enabled(config, alert_type):
                continue

            expires = _naive(doc.expires_at)
            days_left = (expires - now).days
            if days_left > threshold:
                continue

            if days_left < 0:
                severity = AlertSeverity.critical
                msg = f"{label} expire depuis {abs(days_left)} jour(s)."
            elif days_left <= threshold // 3:
                severity = AlertSeverity.critical
                msg = f"{label} expire dans {days_left} jour(s)."
            else:
                severity = AlertSeverity.warning
                msg = f"{label} expire dans {days_left} jour(s)."

            # Dedup by document + expiry date (re-alerts only if expiry changes)
            dedup = f"doc:{doc.id}:{alert_type.value}:{expires.date().isoformat()}"
            alert = await self._emit(
                db,
                dossier.id,
                alert_type,
                severity,
                f"{label} - echeance",
                msg,
                dedup,
                {"document_id": doc.id, "days_left": days_left},
            )
            if alert:
                created.append(alert)

        return created

    async def scan_submission_deadline(
        self, db: AsyncSession, dossier: Dossier, config: AlertConfig | None
    ) -> list[Alert]:
        """Alert when a dossier's submission deadline approaches.

        Uses extra field on dossier if present; otherwise derives nothing.
        """
        if not self._type_enabled(config, AlertType.submission_deadline):
            return []

        deadline = getattr(dossier, "submission_deadline", None)
        if deadline is None:
            return []

        now = self._now_naive()
        deadline_naive = _naive(deadline)
        days_left = (deadline_naive - now).days
        if days_left > SUBMISSION_DEADLINE_DAYS or days_left < 0:
            return []

        severity = (
            AlertSeverity.critical if days_left <= 7 else AlertSeverity.warning
        )
        dedup = f"deadline:{dossier.id}:{deadline_naive.date().isoformat()}"
        alert = await self._emit(
            db,
            dossier.id,
            AlertType.submission_deadline,
            severity,
            "Deadline de soumission",
            f"La soumission du dossier approche: {days_left} jour(s) restant(s).",
            dedup,
            {"days_left": days_left},
        )
        return [alert] if alert else []

    async def scan_express_entry_round(
        self,
        db: AsyncSession,
        dossier: Dossier,
        config: AlertConfig | None,
        latest_round: dict[str, Any] | None,
        candidate_crs: int | None,
    ) -> list[Alert]:
        """Alert when a new EE round has a cutoff at or below the candidate's score."""
        if not self._type_enabled(config, AlertType.express_entry_round):
            return []
        if latest_round is None or candidate_crs is None:
            return []

        cutoff = latest_round.get("score")
        if cutoff is None or candidate_crs < cutoff:
            return []

        round_date = latest_round.get("date", "")
        dedup = f"eeround:{dossier.id}:{round_date}"
        alert = await self._emit(
            db,
            dossier.id,
            AlertType.express_entry_round,
            AlertSeverity.info,
            "Nouvelle ronde Express Entry compatible",
            (
                f"Ronde du {round_date}: seuil {cutoff}. "
                f"Votre score CRS ({candidate_crs}) est admissible."
            ),
            dedup,
            {"cutoff": cutoff, "candidate_crs": candidate_crs, "round": latest_round},
        )
        return [alert] if alert else []

    async def scan_policy_change(
        self,
        db: AsyncSession,
        dossier: Dossier,
        config: AlertConfig | None,
        update: Any,
    ) -> list[Alert]:
        """Alert on an IRCC policy update that impacts this dossier."""
        if not self._type_enabled(config, AlertType.policy_change):
            return []
        if update is None:
            return []

        dedup = f"policy:{dossier.id}:{update.id}"
        alert = await self._emit(
            db,
            dossier.id,
            AlertType.policy_change,
            AlertSeverity.warning,
            "Changement de politique IRCC",
            update.summary or update.title,
            dedup,
            {"ircc_update_id": update.id},
        )
        return [alert] if alert else []

    async def scan_deadlines(
        self, db: AsyncSession, dossier: Dossier, config: AlertConfig | None
    ) -> list[Alert]:
        """Alert on open (not completed) Deadline milestones approaching.

        Each deadline type has its own alerting window and emits at the
        type's AlertType. Severity escalates as the due date nears; an
        overdue deadline is critical.
        """
        now = self._now_naive()
        created: list[Alert] = []

        result = await db.execute(
            select(Deadline).where(
                Deadline.dossier_id == dossier.id,
                Deadline.is_completed == False,  # noqa: E712
            )
        )
        deadlines = result.scalars().all()

        for dl in deadlines:
            rule = DEADLINE_RULES.get(dl.deadline_type)
            if rule is None:
                continue
            alert_type, window, label = rule
            if not self._type_enabled(config, alert_type):
                continue

            due = _naive(dl.due_date)
            days_left = (due - now).days
            if days_left > window:
                continue

            if days_left < 0:
                severity = AlertSeverity.critical
                msg = f"{label}: echeance depassee depuis {abs(days_left)} jour(s)."
            elif days_left <= max(window // 6, 3):
                severity = AlertSeverity.critical
                msg = f"{label}: {days_left} jour(s) restant(s)."
            else:
                severity = AlertSeverity.warning
                msg = f"{label}: {days_left} jour(s) restant(s)."

            # Re-alert only if the due date changes.
            dedup = f"deadline:{dl.id}:{alert_type.value}:{due.date().isoformat()}"
            alert = await self._emit(
                db,
                dossier.id,
                alert_type,
                severity,
                f"{label} - echeance",
                msg,
                dedup,
                {"deadline_id": dl.id, "days_left": days_left},
            )
            if alert:
                created.append(alert)

        return created

    async def scan_dossier(
        self,
        db: AsyncSession,
        dossier: Dossier,
        candidate_crs: int | None = None,
        latest_round: dict[str, Any] | None = None,
    ) -> list[Alert]:
        """Run all applicable scans for a single dossier."""
        # Skip terminal dossiers
        if dossier.status in (
            DossierStatus.approuve,
            DossierStatus.refuse,
            DossierStatus.archive,
        ):
            return []

        config = await self._config_for(dossier.id, db)
        if config is not None and not config.is_enabled:
            return []

        created: list[Alert] = []
        created += await self.scan_document_expiries(db, dossier, config)
        created += await self.scan_submission_deadline(db, dossier, config)
        created += await self.scan_deadlines(db, dossier, config)
        if candidate_crs is not None and latest_round is not None:
            created += await self.scan_express_entry_round(
                db, dossier, config, latest_round, candidate_crs
            )
        return created

    async def scan_all(
        self, db: AsyncSession, latest_round: dict[str, Any] | None = None
    ) -> int:
        """Scan every active dossier. Returns number of new alerts created."""
        result = await db.execute(select(Dossier))
        dossiers = result.scalars().all()

        total = 0
        for dossier in dossiers:
            alerts = await self.scan_dossier(db, dossier, latest_round=latest_round)
            total += len(alerts)
        await db.commit()
        return total

    # ------------------------------------------------------------------ #
    # Delivery
    # ------------------------------------------------------------------ #

    def _channels_for(
        self, config: AlertConfig | None, severity: AlertSeverity
    ) -> dict[str, bool]:
        """Resolve the active channels for an alert.

        Uses the dossier's AlertConfig.channels (or defaults). A ``critical``
        alert always forces dashboard + email on, even if disabled, so a
        time-sensitive condition is never silently withheld.
        """
        channels = dict(DEFAULT_CHANNELS)
        if config is not None and config.channels:
            channels.update(config.channels)
        if severity == AlertSeverity.critical:
            channels["dashboard"] = True
            channels["email"] = True
        return channels

    async def _recipient_for(
        self, db: AsyncSession, dossier: Dossier
    ) -> User | None:
        """The user who should receive alerts for a dossier.

        Prefers the assigned consultant; falls back to the first active admin.
        """
        if dossier.assigned_to is not None:
            result = await db.execute(
                select(User).where(
                    User.id == dossier.assigned_to, User.is_active == True  # noqa: E712
                )
            )
            user = result.scalar_one_or_none()
            if user is not None:
                return user

        result = await db.execute(
            select(User)
            .where(User.role == UserRole.admin, User.is_active == True)  # noqa: E712
            .order_by(User.id)
        )
        return result.scalars().first()

    async def deliver_pending(self, db: AsyncSession) -> dict[str, int]:
        """Deliver all un-notified alerts across their configured channels.

        - dashboard → persisted as a channel-tagged Notification row, which the
          consultant dashboard reads.
        - email → same Notification row, plus an actual SMTP send when a relay
          is configured. Without one it stays dashboard-visible only, and
          `email_sent` reports how many messages really went out.
        - whatsapp → sent via Twilio when configured; skipped gracefully
          otherwise.

        Returns per-channel delivery counts. Marks alerts is_notified=True.
        """
        stats = {"dashboard": 0, "email": 0, "email_sent": 0, "whatsapp": 0, "alerts": 0}

        result = await db.execute(
            select(Alert).where(
                Alert.is_notified == False,  # noqa: E712
                Alert.is_dismissed == False,  # noqa: E712
            )
        )
        alerts = result.scalars().all()

        # Cache recipient/config lookups per dossier within one delivery pass.
        recipients: dict[int, User | None] = {}
        configs: dict[int, AlertConfig | None] = {}

        for alert in alerts:
            did = alert.dossier_id
            if did not in configs:
                configs[did] = await self._config_for(did, db)
            if did not in recipients:
                dres = await db.execute(select(Dossier).where(Dossier.id == did))
                dossier = dres.scalar_one_or_none()
                recipients[did] = (
                    await self._recipient_for(db, dossier) if dossier else None
                )

            recipient = recipients[did]
            channels = self._channels_for(configs[did], alert.severity)

            delivered_any = False

            # Dashboard + email are both realized as Notification rows.
            for channel_name, channel_enum in (
                ("dashboard", NotificationChannel.dashboard),
                ("email", NotificationChannel.email),
            ):
                if not channels.get(channel_name):
                    continue
                if recipient is None:
                    continue
                db.add(
                    Notification(
                        recipient_id=recipient.id,
                        dossier_id=did,
                        notification_type=NotificationType.deadline_approaching,
                        channel=channel_enum,
                        title=alert.title,
                        message=alert.message,
                        is_read=False,
                        sent_at=self._now_naive(),
                    )
                )
                stats[channel_name] += 1
                delivered_any = True

                # The email channel additionally leaves the building when a
                # relay is configured. Best-effort: a send failure still leaves
                # the notification visible on the dashboard.
                if channel_name == "email" and smtp_sender.is_configured:
                    res = await smtp_sender.send(
                        to=recipient.email,
                        subject=alert.title,
                        body=alert.message,
                    )
                    if res.get("status") == "sent":
                        stats["email_sent"] += 1

            # WhatsApp via Twilio (best-effort, degrades gracefully).
            if channels.get("whatsapp") and whatsapp_service.is_configured:
                to_number = getattr(recipient, "phone", None) if recipient else None
                if to_number:
                    try:
                        res = await whatsapp_service.notify(
                            event=NotificationEvent.DEADLINE_APPROACHING,
                            to_number=to_number,
                            data={
                                "candidate_name": "",
                                "dossier_ref": str(did),
                                "deadline_date": "",
                                "days_remaining": (alert.extra_data or {}).get(
                                    "days_left", ""
                                ),
                            },
                        )
                        if res.get("status") == "sent":
                            stats["whatsapp"] += 1
                            delivered_any = True
                    except Exception:
                        # Never let a delivery channel failure abort the pass.
                        pass

            if delivered_any or recipient is None:
                # Mark notified even when no recipient exists so we don't
                # re-scan the same alert forever; dedup_key still prevents
                # duplicate alert creation.
                alert.is_notified = True
                stats["alerts"] += 1

        await db.commit()
        return stats

    async def scan_and_deliver(
        self, db: AsyncSession, latest_round: dict[str, Any] | None = None
    ) -> dict[str, int]:
        """Convenience: run a full scan then deliver pending alerts."""
        created = await self.scan_all(db, latest_round=latest_round)
        stats = await self.deliver_pending(db)
        stats["new_alerts"] = created
        return stats


# Singleton
alert_service = AlertService()
