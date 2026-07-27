"""Schemas for compliance verification API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ComplianceIssue(BaseModel):
    document: str | None = None
    field: str | None = None
    documents: list[str] | None = None
    issue: str
    severity: str = Field(pattern="^(high|medium|low)$")


class ComplianceBreakdownItem(BaseModel):
    score: float = Field(ge=0, le=100)
    weight: float
    weighted_score: float


class ComplianceBreakdown(BaseModel):
    completeness: ComplianceBreakdownItem
    validity: ComplianceBreakdownItem
    consistency: ComplianceBreakdownItem


class ComplianceRecommendation(BaseModel):
    priority: str = Field(pattern="^(high|medium|low)$")
    action: str


class IssuesCount(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0


class ComplianceScoreResponse(BaseModel):
    global_score: float = Field(ge=0, le=100)
    status: str
    color: str
    is_ready_for_submission: bool
    breakdown: ComplianceBreakdown
    issues_count: IssuesCount
    recommendations: list[ComplianceRecommendation]
    summary: str
    method: str
    verified_at: str


class ComplianceVerifyRequest(BaseModel):
    """Optional request body to override default behavior."""
    force_refresh: bool = False


class ComplianceHistoryEntry(BaseModel):
    score: float
    status: str
    verified_at: datetime
    method: str


class ComplianceStatusResponse(BaseModel):
    dossier_id: int
    program_name: str
    current_score: float | None
    last_verified_at: datetime | None
    status: str
    documents_count: int
    missing_mandatory: list[str]
