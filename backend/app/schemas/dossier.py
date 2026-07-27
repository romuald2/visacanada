from datetime import datetime

from pydantic import BaseModel, Field

from app.models.dossier import DossierStatus


class DossierCreate(BaseModel):
    candidate_id: int
    program_id: int
    assigned_to: int | None = None
    notes: str | None = None


class DossierUpdate(BaseModel):
    status: DossierStatus | None = None
    assigned_to: int | None = None
    compliance_score: float | None = Field(None, ge=0, le=100)
    reference_number: str | None = None
    notes: str | None = None


class DossierResponse(BaseModel):
    id: int
    candidate_id: int
    program_id: int
    assigned_to: int | None
    status: DossierStatus
    compliance_score: float | None
    reference_number: str | None
    notes: str | None
    submitted_at: datetime | None
    decision_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
