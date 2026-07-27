"""Pydantic schemas for program requirements and versioning."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.program_requirement import RequirementPriority


class ProgramRequirementCreate(BaseModel):
    program_id: int
    document_type: str = Field(min_length=1, max_length=100)
    document_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: RequirementPriority = RequirementPriority.mandatory
    imm_form_reference: str | None = None
    sort_order: int = 0
    notes: str | None = None


class ProgramRequirementUpdate(BaseModel):
    document_type: str | None = Field(None, min_length=1, max_length=100)
    document_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: RequirementPriority | None = None
    imm_form_reference: str | None = None
    sort_order: int | None = None
    notes: str | None = None
    is_active: bool | None = None
    change_reason: str | None = None


class ProgramRequirementResponse(BaseModel):
    id: int
    program_id: int
    document_type: str
    document_name: str
    description: str | None
    priority: RequirementPriority
    imm_form_reference: str | None
    sort_order: int
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RequirementChangeResponse(BaseModel):
    id: int
    requirement_id: int
    changed_by: int | None
    field_name: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgramListResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str
    description: str | None
    processing_time_days: int | None
    government_fee: float | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
