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

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import (
    Alert,
    AlertConfig,
    AlertSeverity,
    AlertType,
)
from app.models.document import Document, DocumentType
from app.models.dossier import Dossier, DossierStatus

# Thresholds (days)
PASSPORT_EXPIRY_DAYS = 180  # 6 months
MEDICAL_EXPIRY_DAYS = 60
LANGUAGE_EXPIRY_DAYS = 90
SUBMISSION_DEADLINE_DAYS = 30


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


# Singleton
alert_service = AlertService()
