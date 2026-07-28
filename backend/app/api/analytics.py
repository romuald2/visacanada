"""Analytics and reporting API."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

_roles = require_role(UserRole.admin, UserRole.consultant)


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Counts of active / approved / refused / archived dossiers."""
    return await analytics_service.overview(db)


@router.get("/success-rate")
async def success_rate(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Approval rate per program."""
    return await analytics_service.success_rate_by_program(db)


@router.get("/processing-time")
async def processing_time(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Average processing time overall and per program."""
    return await analytics_service.avg_processing_time(db)


@router.get("/revenue")
async def revenue(
    period: str = Query(default="month", pattern="^(month|year)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Estimated revenue by period."""
    return await analytics_service.revenue_by_period(db, period)


@router.get("/workload-forecast")
async def workload_forecast(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Forecast of expected decisions from active dossiers."""
    return await analytics_service.workload_forecast(db)


@router.get("/export/csv")
async def export_csv(
    report: str = Query(default="success-rate", pattern="^(success-rate|processing-time|revenue)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Export an analytics report as CSV."""
    if report == "success-rate":
        rows = await analytics_service.success_rate_by_program(db)
    elif report == "processing-time":
        data = await analytics_service.avg_processing_time(db)
        rows = data["by_program"]
    else:  # revenue
        data = await analytics_service.revenue_by_period(db)
        rows = data["series"]

    csv_bytes = analytics_service.to_csv(rows)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{report}.csv"'
        },
    )


@router.get("/export/pdf")
async def export_pdf(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Export a full analytics report as PDF."""
    overview_data = await analytics_service.overview(db)
    success = await analytics_service.success_rate_by_program(db)
    proc = await analytics_service.avg_processing_time(db)
    rev = await analytics_service.revenue_by_period(db)

    sections = [
        {"heading": "Vue d'ensemble", "rows": [overview_data]},
        {"heading": "Taux de reussite par programme", "rows": success},
        {"heading": "Temps de traitement par programme", "rows": proc["by_program"]},
        {"heading": "Revenus par periode", "rows": rev["series"]},
    ]
    pdf_bytes = analytics_service.report_pdf("Rapport analytique - VisaCanada", sections)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rapport_analytique.pdf"'
        },
    )
