"""Events group related measurements (a day, a night, a workout block)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class Event(UUIDMixin, TimestampMixin, Base):
    """A logical grouping of measurements for one moment/context."""

    __tablename__ = "events"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(32), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_key: Mapped[date] = mapped_column(Date, index=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONColumn, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="manual")
