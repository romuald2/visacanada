import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class ImmigrationProgram(str, enum.Enum):
    express_entry_fsw = "express_entry_fsw"
    express_entry_cec = "express_entry_cec"
    express_entry_fst = "express_entry_fst"
    pnp = "pnp"
    iec_working_holiday = "iec_working_holiday"
    iec_young_professionals = "iec_young_professionals"
    iec_coop = "iec_coop"
    study_permit = "study_permit"
    work_permit_lmia = "work_permit_lmia"
    work_permit_imp = "work_permit_imp"
    family_spouse = "family_spouse"
    family_parent = "family_parent"
    family_child = "family_child"
    super_visa = "super_visa"
    visitor_visa = "visitor_visa"
    refugee = "refugee"


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(
        Enum(ImmigrationProgram), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_time_days: Mapped[int | None] = mapped_column(nullable=True)
    government_fee: Mapped[float | None] = mapped_column(nullable=True)
    documents_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    dossiers = relationship("Dossier", back_populates="program")

    def __repr__(self) -> str:
        return f"<Program(id={self.id}, code={self.code}, name={self.name})>"
