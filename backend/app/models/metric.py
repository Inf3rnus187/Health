"""The dynamic metric registry — extensible without migrations.

Adding a metric is a row insert here (via UI, API or the AI), never a
schema change. Values live in :mod:`app.models.measurement`.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class MetricDefinition(UUIDMixin, TimestampMixin, Base):
    """Definition of one measurable quantity (a field)."""

    __tablename__ = "metric_definitions"

    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(160))
    domain: Mapped[str] = mapped_column(String(40), index=True)
    data_type: Mapped[str] = mapped_column(String(16))
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    enum_options: Mapped[list[Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    aggregation_hint: Mapped[str] = mapped_column(String(8), default="avg")
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
