"""IRCCUpdate model - stores detected IRCC policy updates and changes."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class IRCCUpdateCategory(str, enum.Enum):
    new_program = "new_program"
    criteria_change = "criteria_change"
    processing_time = "processing_time"
    policy_update = "policy_update"
    fee_change = "fee_change"
    form_update = "form_update"
    general_news = "general_news"


class IRCCUpdateSource(str, enum.Enum):
    atom_feed = "atom_feed"
    processing_times = "processing_times"
    manual = "manual"


class IRCCUpdate(Base):
    __tablename__ = "ircc_updates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[IRCCUpdateCategory] = mapped_column(
        Enum(IRCCUpdateCategory), default=IRCCUpdateCategory.general_news, nullable=False
    )
    source: Mapped[IRCCUpdateSource] = mapped_column(
        Enum(IRCCUpdateSource), default=IRCCUpdateSource.atom_feed, nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<IRCCUpdate(id={self.id}, category={self.category}, "
            f"title={self.title[:50]})>"
        )
