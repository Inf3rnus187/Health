"""Progress photos and their AI analyses (pipeline built in Phase 4).

Only the fixed schema lives here; the ingest/normalize/analyse pipeline
is added later without touching these tables.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class Photo(UUIDMixin, TimestampMixin, Base):
    """An original + normalized progress photo for one angle/day."""

    __tablename__ = "photos"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_key: Mapped[date] = mapped_column(Date, index=True)
    original_path: Mapped[str] = mapped_column(String(512))
    normalized_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    angle: Mapped[str] = mapped_column(String(16), default="face")
    exif: Mapped[dict[str, Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )
    scale_reference: Mapped[dict[str, Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )
    linked_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="received")


class PhotoAnalysis(UUIDMixin, TimestampMixin, Base):
    """A versioned AI analysis of one photo."""

    __tablename__ = "photo_analyses"

    photo_id: Mapped[str] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), index=True
    )
    model: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(32))
    raw_output: Mapped[dict[str, Any]] = mapped_column(JSONColumn, default=dict)
    derived_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )
    comparison_ref: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
