"""Work sessions: clock-in / clock-out times (occupational health)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkSession(UUIDMixin, TimestampMixin, Base):
    """One stretch at work: clocked in, then out (open while at work)."""

    __tablename__ = "work_sessions"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    #: None while the user is still at work.
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: tap (one-tap / GPS shortcut), manual (web, assistant) or import.
    source: Mapped[str] = mapped_column(String(16), default="manual")
    note: Mapped[str] = mapped_column(String(200), default="")

    __table_args__ = (
        Index("uq_work_user_start", "user_id", "start_at", unique=True),
    )
