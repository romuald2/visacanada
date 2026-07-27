from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class CandidateCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    passport_number: str | None = None
    current_country: str | None = None
    current_city: str | None = None
    language_french: str | None = None
    language_english: str | None = None
    notes: str | None = None


class CandidateUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    passport_number: str | None = None
    current_country: str | None = None
    current_city: str | None = None
    language_french: str | None = None
    language_english: str | None = None
    notes: str | None = None


class CandidateResponse(BaseModel):
    id: int
    user_id: int | None
    first_name: str
    last_name: str
    email: str
    phone: str | None
    date_of_birth: date | None
    nationality: str | None
    passport_number: str | None
    current_country: str | None
    current_city: str | None
    language_french: str | None
    language_english: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
