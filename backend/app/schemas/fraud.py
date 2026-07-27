"""Schemas for fraud detection API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FraudAlertItem(BaseModel):
    category: str
    severity: str
    description: str
    confidence: float = Field(ge=0, le=1)
    details: dict[str, Any] = {}


class FraudAlertsCount(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0


class FraudAnalysisResponse(BaseModel):
    id: int
    document_id: int
    fraud_score: float = Field(ge=0, le=100)
    risk_level: str
    requires_human_review: bool
    alerts: list[FraudAlertItem]
    alerts_count: FraudAlertsCount
    summary: str
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    analyzed_at: datetime

    model_config = {"from_attributes": True}


class FraudAnalysisCreate(BaseModel):
    """Optional parameters for fraud analysis."""
    include_metadata_check: bool = True
    include_mrz_check: bool = True
    include_logical_check: bool = True
    include_pattern_check: bool = True


class FraudReviewRequest(BaseModel):
    """Request to review a fraud alert."""
    status: str = Field(pattern="^(reviewed_legitimate|reviewed_suspicious|reviewed_fraudulent)$")
    notes: str | None = None


class FraudAlertListResponse(BaseModel):
    id: int
    document_id: int
    fraud_score: float
    risk_level: str
    requires_human_review: bool
    status: str
    summary: str | None
    analyzed_at: datetime

    model_config = {"from_attributes": True}


class FraudStatsResponse(BaseModel):
    total_analyses: int
    pending_review: int
    reviewed: int
    by_risk_level: dict[str, int]
    average_score: float
