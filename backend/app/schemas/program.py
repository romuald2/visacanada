from datetime import datetime

from pydantic import BaseModel

from app.models.program import ImmigrationProgram


class ProgramCreate(BaseModel):
    code: ImmigrationProgram
    name: str
    description: str | None = None
    category: str
    processing_time_days: int | None = None
    government_fee: float | None = None
    documents_required: str | None = None
    eligibility_criteria: str | None = None


class ProgramResponse(BaseModel):
    id: int
    code: ImmigrationProgram
    name: str
    description: str | None
    category: str
    processing_time_days: int | None
    government_fee: float | None
    documents_required: str | None
    eligibility_criteria: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
