"""Configurable external-key → metric-key mappings (§7.1).

Lets new HealthKit/CPAP fields be absorbed with no code change: a row here
maps an external key (e.g. ``HKQuantityTypeIdentifierBodyMass``) to a metric
key. A ``NULL`` ``user_id`` is a global default; a user row overrides it.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class IngestMapping(UUIDMixin, TimestampMixin, Base):
    """One external-key → metric-key mapping for an ingest source."""

    __tablename__ = "ingest_mappings"

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(16), index=True)
    external_key: Mapped[str] = mapped_column(String(128), index=True)
    metric_key: Mapped[str] = mapped_column(String(80))

    __table_args__ = (Index("ix_ingest_map_lookup", "source", "external_key"),)
