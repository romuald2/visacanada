"""Fraud detection API router."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status


def _utcnow() -> datetime:
    """Naive UTC timestamp (matches the rest of the codebase)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.dossier import Dossier
from app.models.fraud_analysis import FraudAlertStatus, FraudAnalysis, FraudRiskLevel
from app.models.user import User, UserRole
from app.schemas.fraud import (
    FraudAlertListResponse,
    FraudAnalysisCreate,
    FraudAnalysisResponse,
    FraudReviewRequest,
    FraudStatsResponse,
)
from app.services.fraud_detection import fraud_detection_service

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.post(
    "/documents/{document_id}/analyze",
    response_model=FraudAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_document_fraud(
    document_id: int,
    body: FraudAnalysisCreate | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Run fraud detection analysis on a document.

    Never auto-rejects. Flags suspicious documents for human review.
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )

    # Parse extracted data
    extracted_data = None
    if document.extracted_data:
        try:
            extracted_data = (
                json.loads(document.extracted_data)
                if isinstance(document.extracted_data, str)
                else document.extracted_data
            )
        except (json.JSONDecodeError, TypeError):
            extracted_data = None

    # Build PDF metadata from what we know
    pdf_metadata = None  # Would come from actual PDF parsing in production

    # Build file metadata
    file_metadata = {
        "file_size_bytes": document.file_size_bytes,
        "mime_type": document.mime_type,
    }

    # Run fraud analysis
    doc_type = document.document_type.value if hasattr(document.document_type, "value") else document.document_type
    analysis_result = fraud_detection_service.analyze_document(
        document_type=doc_type,
        extracted_data=extracted_data,
        pdf_metadata=pdf_metadata,
        file_metadata=file_metadata,
    )

    # Store result
    fraud_analysis = FraudAnalysis(
        document_id=document_id,
        fraud_score=analysis_result["fraud_score"],
        risk_level=FraudRiskLevel(analysis_result["risk_level"]),
        requires_human_review=analysis_result["requires_human_review"],
        alerts=analysis_result["alerts"],
        alerts_count=analysis_result["alerts_count"],
        summary=analysis_result["summary"],
        status=FraudAlertStatus.pending_review,
    )
    db.add(fraud_analysis)

    # Update document fraud score
    document.fraud_score = analysis_result["fraud_score"]

    # Log to audit
    audit = AuditLog(
        user_id=current_user.id,
        action="fraud_analysis",
        entity_type="document",
        entity_id=document_id,
        details=json.dumps({
            "fraud_score": analysis_result["fraud_score"],
            "risk_level": analysis_result["risk_level"],
            "alerts_count": analysis_result["alerts_count"]["total"],
        }),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(fraud_analysis)

    return fraud_analysis


@router.get(
    "/documents/{document_id}/report",
    response_model=FraudAnalysisResponse,
)
async def get_fraud_report(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get the latest fraud analysis report for a document."""
    result = await db.execute(
        select(FraudAnalysis)
        .where(FraudAnalysis.document_id == document_id)
        .order_by(FraudAnalysis.analyzed_at.desc())
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune analyse de fraude trouvée pour ce document",
        )

    return analysis


@router.get(
    "/alerts",
    response_model=list[FraudAlertListResponse],
)
async def list_fraud_alerts(
    status_filter: FraudAlertStatus | None = Query(None, alias="status"),
    risk_level: FraudRiskLevel | None = None,
    requires_review: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List fraud alerts with filters. Primarily for human review queue."""
    query = select(FraudAnalysis)

    if status_filter:
        query = query.where(FraudAnalysis.status == status_filter)
    if risk_level:
        query = query.where(FraudAnalysis.risk_level == risk_level)
    if requires_review is not None:
        query = query.where(FraudAnalysis.requires_human_review == requires_review)

    query = query.order_by(FraudAnalysis.fraud_score.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.put(
    "/alerts/{alert_id}/review",
    response_model=FraudAnalysisResponse,
)
async def review_fraud_alert(
    alert_id: int,
    body: FraudReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Mark a fraud alert as reviewed (admin only). Never auto-rejects."""
    result = await db.execute(
        select(FraudAnalysis).where(FraudAnalysis.id == alert_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte de fraude non trouvée",
        )

    analysis.status = FraudAlertStatus(body.status)
    analysis.reviewed_by = current_user.id
    analysis.reviewed_at = _utcnow()
    analysis.review_notes = body.notes

    # Log to audit
    audit = AuditLog(
        user_id=current_user.id,
        action="fraud_review",
        entity_type="fraud_analysis",
        entity_id=alert_id,
        details=json.dumps({
            "status": body.status,
            "document_id": analysis.document_id,
            "notes": body.notes,
        }),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(analysis)

    return analysis


@router.get(
    "/stats",
    response_model=FraudStatsResponse,
)
async def get_fraud_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Get fraud detection statistics (admin only)."""
    # Total analyses
    total_result = await db.execute(
        select(func.count(FraudAnalysis.id))
    )
    total = total_result.scalar() or 0

    # Pending review
    pending_result = await db.execute(
        select(func.count(FraudAnalysis.id)).where(
            FraudAnalysis.status == FraudAlertStatus.pending_review
        )
    )
    pending = pending_result.scalar() or 0

    # By risk level
    risk_counts = {}
    for level in FraudRiskLevel:
        count_result = await db.execute(
            select(func.count(FraudAnalysis.id)).where(
                FraudAnalysis.risk_level == level
            )
        )
        risk_counts[level.value] = count_result.scalar() or 0

    # Average score
    avg_result = await db.execute(
        select(func.avg(FraudAnalysis.fraud_score))
    )
    avg_score = avg_result.scalar() or 0.0

    return FraudStatsResponse(
        total_analyses=total,
        pending_review=pending,
        reviewed=total - pending,
        by_risk_level=risk_counts,
        average_score=round(float(avg_score), 1),
    )
