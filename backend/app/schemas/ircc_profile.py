"""Schemas for IRCC profile pre-fill API."""

from typing import Any

from pydantic import BaseModel


class IRCCFieldResponse(BaseModel):
    ircc_field: str
    label: str
    value: Any | None = None
    required: bool
    filled: bool
    valid: bool | None = None
    format: str | None = None


class MissingFieldResponse(BaseModel):
    field: str
    label: str
    section: str


class ValidationErrorResponse(BaseModel):
    field: str
    label: str
    value: str
    error: str


class IRCCProfileResponse(BaseModel):
    program_category: str
    sections: dict[str, list[IRCCFieldResponse]]
    completeness_percent: float
    total_fields: int
    filled_fields: int
    missing_required: list[MissingFieldResponse]
    validation_errors: list[ValidationErrorResponse]
    is_ready: bool
    generated_at: str


class IRCCProfileExportResponse(BaseModel):
    program: str
    generated_at: str
    fields: dict[str, dict[str, Any]]


class SubmissionGuideStep(BaseModel):
    step: int
    title: str
    description: str | None = None
    url: str | None = None


class SubmissionGuideResponse(BaseModel):
    program_category: str
    steps: list[SubmissionGuideStep]
