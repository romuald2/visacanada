"""PIPEDA compliance service: data-subject access, erasure, breach assessment.

Implements the data-handling logic behind the privacy API:
- export_user_data: assemble a portable copy of everything held about a user
  (access right / data portability).
- erase_user_data: delete or anonymize a user's personal data (right to
  erasure), preserving records that must be retained for legal/audit reasons.
- assess_breach_notification: decide whether a breach meets the "real risk of
  significant harm" threshold that triggers mandatory notification.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.privacy import ConsentRecord

# Current privacy-policy / terms version. Bump when the policy text changes so
# prior consents can be re-collected.
PRIVACY_POLICY_VERSION = "1.0.0"


class PrivacyService:
    async def export_user_data(self, user, db: AsyncSession) -> dict[str, Any]:
        """Assemble a portable export of all personal data held about a user."""
        export: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "policy_version": PRIVACY_POLICY_VERSION,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            },
        }

        # Candidate profile(s) linked to this user.
        cand_res = await db.execute(
            select(Candidate).where(Candidate.user_id == user.id)
        )
        candidates = cand_res.scalars().all()
        export["candidates"] = [
            {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone": c.phone,
                "nationality": c.nationality,
                "passport_number": c.passport_number,
                "date_of_birth": c.date_of_birth.isoformat() if c.date_of_birth else None,
            }
            for c in candidates
        ]

        # Consent history.
        consent_res = await db.execute(
            select(ConsentRecord).where(ConsentRecord.user_id == user.id)
        )
        consents = consent_res.scalars().all()
        export["consents"] = [
            {
                "consent_type": ct.consent_type.value
                if hasattr(ct.consent_type, "value")
                else ct.consent_type,
                "granted": ct.granted,
                "policy_version": ct.policy_version,
                "granted_at": ct.granted_at.isoformat() if ct.granted_at else None,
                "revoked_at": ct.revoked_at.isoformat() if ct.revoked_at else None,
            }
            for ct in consents
        ]

        return export

    async def erase_user_data(self, user, db: AsyncSession) -> dict[str, Any]:
        """Erase/anonymize a user's personal data (right to erasure).

        Candidate PII is anonymized rather than hard-deleted so that linked
        immigration files keep referential integrity; consent records are
        removed. Audit logs are intentionally retained for legal accountability.
        """
        cand_res = await db.execute(
            select(Candidate).where(Candidate.user_id == user.id)
        )
        candidates = cand_res.scalars().all()
        anonymized = 0
        for c in candidates:
            c.first_name = "SUPPRIME"
            c.last_name = "SUPPRIME"
            c.email = f"deleted+{c.id}@anonymized.local"
            c.phone = None
            c.passport_number = None
            c.nationality = None
            c.notes = None
            c.user_id = None
            anonymized += 1

        await db.execute(delete(ConsentRecord).where(ConsentRecord.user_id == user.id))
        await db.commit()

        return {
            "detail": "Donnees personnelles supprimees/anonymisees",
            "candidates_anonymized": anonymized,
        }

    def assess_breach_notification(
        self, severity: str, affected_users_count: int, sensitive_data: bool
    ) -> bool:
        """Decide if a breach requires notification (real risk of significant harm).

        Under PIPEDA, notification is mandatory when a breach creates a real risk
        of significant harm. We treat high/critical severity, any breach touching
        sensitive data, or a broad blast radius as crossing that threshold.
        """
        if severity in ("high", "critical"):
            return True
        if sensitive_data:
            return True
        if affected_users_count >= 100:
            return True
        return False


# Singleton
privacy_service = PrivacyService()
