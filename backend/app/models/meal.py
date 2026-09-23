"""Meals logged in the journal (time, type, description, photo, AI)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class Meal(UUIDMixin, TimestampMixin, Base):
    """One meal: when, which, what the user wrote, its photo and reading."""

    __tablename__ = "meals"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_key: Mapped[date] = mapped_column(Date)
    #: breakfast, lunch, dinner or snack.
    meal_type: Mapped[str] = mapped_column(String(16), default="lunch")
    description: Mapped[str] = mapped_column(Text, default="")
    #: What it cost (a delivery, a sandwich bought late) and from whom.
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    vendor: Mapped[str] = mapped_column(String(120), default="")
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    #: AI reading: None (never), queued, running, done or failed.
    analysis_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    #: Items, nutrients (checked), assessment — see meal_ai.
    analysis: Mapped[dict[str, Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )

    __table_args__ = (Index("ix_meals_user_eaten", "user_id", "eaten_at"),)

    @property
    def has_photo(self) -> bool:
        """Whether a photo is attached."""
        return bool(self.photo_path)
