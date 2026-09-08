"""Declarative base, portable column types and shared mixins.

The generic ``JSON`` type maps to native ``JSONB`` on PostgreSQL and to
``JSON`` on SQLite, so the same models run in production and in tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: JSON column that becomes ``JSONB`` on PostgreSQL.
JSONColumn = JSON().with_variant(JSONB(), "postgresql")


def new_uuid() -> str:
    """Return a new random UUID rendered as a string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Return ``value`` as aware UTC (SQLite reads back naive)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


class UUIDMixin:
    """Adds a string UUID primary key."""

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid
    )


class TimestampMixin:
    """Adds a ``created_at`` audit timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
