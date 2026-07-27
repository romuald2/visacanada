"""Compliance Scoring Engine.

Aggregates compliance verification results into a weighted score (0-100%).
Tracks score history for dossier progression monitoring.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dossier import Dossier
from app.models.document import Document


class ScoringEngine:
    """Calculates and tracks compliance scores for dossiers."""

    # Weight distribution for global score
    WEIGHTS = {
        "completeness": 0.4,
        "validity": 0.3,
        "consistency": 0.3,
    }

    # Score thresholds
    THRESHOLD_READY = 85.0  # Dossier ready for submission
    THRESHOLD_WARNING = 60.0  # Needs attention
    THRESHOLD_CRITICAL = 40.0  # Major issues

    def calculate_global_score(self, compliance_report: dict[str, Any]) -> float:
        """Calculate weighted global score from compliance report."""
        completeness = compliance_report.get("completeness", {}).get("score", 0)
        validity = compliance_report.get("validity", {}).get("score", 0)
        consistency = compliance_report.get("consistency", {}).get("score", 0)

        global_score = (
            completeness * self.WEIGHTS["completeness"]
            + validity * self.WEIGHTS["validity"]
            + consistency * self.WEIGHTS["consistency"]
        )

        return round(min(100.0, max(0.0, global_score)), 1)

    def get_score_status(self, score: float) -> str:
        """Determine status label from score value."""
        if score >= self.THRESHOLD_READY:
            return "ready"
        elif score >= self.THRESHOLD_WARNING:
            return "warning"
        elif score >= self.THRESHOLD_CRITICAL:
            return "critical"
        return "incomplete"

    def get_score_color(self, score: float) -> str:
        """Return color code for UI display."""
        if score >= self.THRESHOLD_READY:
            return "green"
        elif score >= self.THRESHOLD_WARNING:
            return "orange"
        elif score >= self.THRESHOLD_CRITICAL:
            return "red"
        return "gray"

    def build_score_summary(self, compliance_report: dict[str, Any]) -> dict[str, Any]:
        """Build a structured score summary for API responses."""
        global_score = self.calculate_global_score(compliance_report)
        status = self.get_score_status(global_score)

        completeness = compliance_report.get("completeness", {})
        validity = compliance_report.get("validity", {})
        consistency = compliance_report.get("consistency", {})
        recommendations = compliance_report.get("recommendations", [])

        # Count issues by severity
        high_issues = sum(
            1 for r in recommendations if r.get("priority") == "high"
        )
        medium_issues = sum(
            1 for r in recommendations if r.get("priority") == "medium"
        )
        low_issues = sum(
            1 for r in recommendations if r.get("priority") == "low"
        )

        return {
            "global_score": global_score,
            "status": status,
            "color": self.get_score_color(global_score),
            "is_ready_for_submission": global_score >= self.THRESHOLD_READY,
            "breakdown": {
                "completeness": {
                    "score": completeness.get("score", 0),
                    "weight": self.WEIGHTS["completeness"],
                    "weighted_score": round(
                        completeness.get("score", 0) * self.WEIGHTS["completeness"], 1
                    ),
                },
                "validity": {
                    "score": validity.get("score", 0),
                    "weight": self.WEIGHTS["validity"],
                    "weighted_score": round(
                        validity.get("score", 0) * self.WEIGHTS["validity"], 1
                    ),
                },
                "consistency": {
                    "score": consistency.get("score", 0),
                    "weight": self.WEIGHTS["consistency"],
                    "weighted_score": round(
                        consistency.get("score", 0) * self.WEIGHTS["consistency"], 1
                    ),
                },
            },
            "issues_count": {
                "high": high_issues,
                "medium": medium_issues,
                "low": low_issues,
                "total": high_issues + medium_issues + low_issues,
            },
            "recommendations": recommendations,
            "summary": compliance_report.get("summary", ""),
            "method": compliance_report.get("method", "ai"),
            "verified_at": datetime.utcnow().isoformat(),
        }

    async def save_score(
        self,
        db: AsyncSession,
        dossier_id: UUID,
        score_summary: dict[str, Any],
    ) -> None:
        """Save compliance score to dossier record."""
        result = await db.execute(
            select(Dossier).where(Dossier.id == dossier_id)
        )
        dossier = result.scalar_one_or_none()

        if dossier:
            dossier.compliance_score = score_summary["global_score"]
            dossier.compliance_details = score_summary
            dossier.last_verified_at = datetime.utcnow()
            await db.commit()

    async def get_dossier_documents_summary(
        self,
        db: AsyncSession,
        dossier_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get documents summary for a dossier to feed into compliance check."""
        result = await db.execute(
            select(Document).where(Document.dossier_id == dossier_id)
        )
        documents = result.scalars().all()

        return [
            {
                "id": str(doc.id),
                "file_name": doc.file_name,
                "document_type": doc.document_type,
                "status": doc.status,
                "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ]


# Singleton
scoring_engine = ScoringEngine()
