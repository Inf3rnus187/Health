"""Fact table: one measured value per row, with no redundancy.

Values are stored in typed columns (not free text) so they stay
queryable and aggregable. Derived and rolling values are computed on
read, never duplicated here (§5.3).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class Measurement(UUIDMixin, TimestampMixin, Base):
    """A single stored value for one metric at one point in time."""

    __tablename__ = "measurements"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_definitions.id", ondelete="CASCADE")
    )
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_key: Mapped[date] = mapped_column(Date)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    value_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )
    source: Mapped[str] = mapped_column(String(16), default="manual")
    token_id: Mapped[str | None] = mapped_column(
        ForeignKey("api_tokens.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_measurements_user_metric_date",
            "user_id",
            "metric_id",
            "date_key",
        ),
        Index("ix_measurements_user_event", "user_id", "event_id"),
        Index(
            "uq_measurement_daily",
            "user_id",
            "metric_id",
            "date_key",
            unique=True,
            sqlite_where=event_id.is_(None),
            postgresql_where=event_id.is_(None),
        ),
        Index(
            "uq_measurement_event",
            "user_id",
            "metric_id",
            "date_key",
            "event_id",
            unique=True,
            sqlite_where=event_id.isnot(None),
            postgresql_where=event_id.isnot(None),
        ),
    )
