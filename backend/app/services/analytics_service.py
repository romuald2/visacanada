"""Analytics service: business performance metrics and reporting.

Computes success rates, processing times, dossier counts, revenue estimates,
and workload forecasts from dossier/program data. Also renders CSV and PDF reports.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dossier import Dossier, DossierStatus
from app.models.program import Program

# Statuses considered "closed" outcomes
APPROVED = DossierStatus.approuve
REFUSED = DossierStatus.refuse
ACTIVE_STATUSES = {
    DossierStatus.nouveau,
    DossierStatus.en_cours,
    DossierStatus.documents_manquants,
    DossierStatus.en_revision,
    DossierStatus.soumis,
}


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


class AnalyticsService:
    """Aggregates dossier data into business analytics."""

    async def overview(self, db: AsyncSession) -> dict[str, Any]:
        """Global counts of active / completed / refused dossiers."""
        result = await db.execute(select(Dossier))
        dossiers = result.scalars().all()

        active = sum(1 for d in dossiers if d.status in ACTIVE_STATUSES)
        approved = sum(1 for d in dossiers if d.status == APPROVED)
        refused = sum(1 for d in dossiers if d.status == REFUSED)
        archived = sum(1 for d in dossiers if d.status == DossierStatus.archive)

        return {
            "total": len(dossiers),
            "active": active,
            "approved": approved,
            "refused": refused,
            "archived": archived,
        }

    async def success_rate_by_program(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Approval rate per program (approved / decided)."""
        prog_result = await db.execute(select(Program))
        programs = {p.id: p for p in prog_result.scalars().all()}

        doss_result = await db.execute(select(Dossier))
        dossiers = doss_result.scalars().all()

        stats: dict[int, dict[str, int]] = {}
        for d in dossiers:
            s = stats.setdefault(d.program_id, {"approved": 0, "refused": 0, "total": 0})
            s["total"] += 1
            if d.status == APPROVED:
                s["approved"] += 1
            elif d.status == REFUSED:
                s["refused"] += 1

        output = []
        for program_id, s in stats.items():
            decided = s["approved"] + s["refused"]
            rate = round(s["approved"] / decided * 100, 1) if decided else None
            program = programs.get(program_id)
            output.append(
                {
                    "program_id": program_id,
                    "program_name": program.name if program else "Inconnu",
                    "category": program.category if program else None,
                    "total": s["total"],
                    "approved": s["approved"],
                    "refused": s["refused"],
                    "success_rate": rate,
                }
            )
        output.sort(key=lambda x: x["total"], reverse=True)
        return output

    async def avg_processing_time(self, db: AsyncSession) -> dict[str, Any]:
        """Average processing time (created -> decision) in days, overall + per program."""
        prog_result = await db.execute(select(Program))
        programs = {p.id: p for p in prog_result.scalars().all()}

        doss_result = await db.execute(select(Dossier))
        dossiers = doss_result.scalars().all()

        overall_days: list[int] = []
        per_program: dict[int, list[int]] = {}

        for d in dossiers:
            if d.decision_at is None or d.created_at is None:
                continue
            days = (_naive(d.decision_at) - _naive(d.created_at)).days
            if days < 0:
                continue
            overall_days.append(days)
            per_program.setdefault(d.program_id, []).append(days)

        def avg(values: list[int]) -> float | None:
            return round(sum(values) / len(values), 1) if values else None

        return {
            "overall_avg_days": avg(overall_days),
            "decided_count": len(overall_days),
            "by_program": [
                {
                    "program_id": pid,
                    "program_name": programs[pid].name if pid in programs else "Inconnu",
                    "avg_days": avg(days),
                    "count": len(days),
                }
                for pid, days in per_program.items()
            ],
        }

    async def revenue_by_period(self, db: AsyncSession, period: str = "month") -> dict[str, Any]:
        """Estimated revenue grouped by period.

        Revenue is estimated from each dossier's program government_fee at the
        dossier creation date. This is a best-effort estimate until the billing
        module (Issue #21) provides actual invoiced amounts.
        """
        prog_result = await db.execute(select(Program))
        programs = {p.id: p for p in prog_result.scalars().all()}

        doss_result = await db.execute(select(Dossier))
        dossiers = doss_result.scalars().all()

        buckets: dict[str, float] = {}
        total = 0.0
        for d in dossiers:
            program = programs.get(d.program_id)
            fee = float(program.government_fee) if program and program.government_fee else 0.0
            if fee == 0.0:
                continue
            created = _naive(d.created_at)
            if created is None:
                continue
            if period == "year":
                key = created.strftime("%Y")
            else:
                key = created.strftime("%Y-%m")
            buckets[key] = buckets.get(key, 0.0) + fee
            total += fee

        series = [{"period": k, "revenue": round(v, 2)} for k, v in sorted(buckets.items())]
        return {
            "period": period,
            "total_revenue": round(total, 2),
            "series": series,
            "note": "Estimation basee sur les frais de programme (module facturation a venir)",
        }

    async def workload_forecast(self, db: AsyncSession) -> dict[str, Any]:
        """Forecast upcoming workload from active dossiers and expected decisions.

        Uses each active dossier's program processing_time_days from creation to
        estimate when decisions are expected, bucketed by month.
        """
        prog_result = await db.execute(select(Program))
        programs = {p.id: p for p in prog_result.scalars().all()}

        doss_result = await db.execute(
            select(Dossier).where(Dossier.status.in_(list(ACTIVE_STATUSES)))
        )
        active = doss_result.scalars().all()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upcoming: dict[str, int] = {}
        for d in active:
            program = programs.get(d.program_id)
            proc_days = (
                program.processing_time_days if program and program.processing_time_days else 180
            )
            base = _naive(d.submitted_at) or _naive(d.created_at) or now
            expected = base + timedelta(days=proc_days)
            key = expected.strftime("%Y-%m")
            upcoming[key] = upcoming.get(key, 0) + 1

        return {
            "active_dossiers": len(active),
            "expected_decisions": [{"period": k, "count": v} for k, v in sorted(upcoming.items())],
        }

    # -------------------------------------------------------------------------
    # Report export
    # -------------------------------------------------------------------------

    def to_csv(self, rows: list[dict[str, Any]]) -> bytes:
        """Render a list of flat dicts to CSV bytes."""
        buffer = io.StringIO()
        if not rows:
            return b""
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8")

    def report_pdf(self, title: str, sections: list[dict[str, Any]]) -> bytes:
        """Render an analytics report to PDF.

        sections: list of {"heading": str, "rows": list[dict]}.
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm)
        styles = getSampleStyleSheet()
        flowables = [Paragraph(title, styles["Title"]), Spacer(1, 0.5 * cm)]

        for section in sections:
            flowables.append(Paragraph(section["heading"], styles["Heading2"]))
            rows = section.get("rows", [])
            if rows:
                headers = list(rows[0].keys())
                data = [headers] + [[str(row.get(h, "")) for h in headers] for row in rows]
                table = Table(data, hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#f0f0f5")],
                            ),
                        ]
                    )
                )
                flowables.append(table)
            else:
                flowables.append(Paragraph("Aucune donnee.", styles["Normal"]))
            flowables.append(Spacer(1, 0.5 * cm))

        doc.build(flowables)
        return buffer.getvalue()


# Singleton
analytics_service = AnalyticsService()
