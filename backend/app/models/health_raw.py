"""Full-fidelity Apple Health storage: every sample, kept raw.

Unlike :mod:`app.models.measurement` (one curated value per day), these
tables keep **every** imported record — millions of quantity/category
samples, plus workouts, ECG traces and GPS routes. Large blobs (ECG
voltages, GPX) live on disk; only metadata is stored here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class HealthSample(UUIDMixin, TimestampMixin, Base):
    """One raw HealthKit sample (quantity or category)."""

    __tablename__ = "health_samples"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_definitions.id", ondelete="CASCADE")
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="apple")
    device: Mapped[str | None] = mapped_column(String(128), nullable=True)
    #: Its id where it comes from (a HealthKit UUID, sent by the iPhone
    #: app): sent again it replaces itself, deleted there it goes here.
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index(
            "ix_samples_user_metric_start", "user_id", "metric_id", "start_at"
        ),
        Index("ix_samples_user_source", "user_id", "source"),
        Index(
            "ux_samples_user_external", "user_id", "external_id", unique=True
        ),
    )


class Workout(UUIDMixin, TimestampMixin, Base):
    """One imported workout session."""

    __tablename__ = "workouts"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    activity_type: Mapped[str] = mapped_column(String(80))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="apple")
    #: Its HealthKit UUID when sent by the iPhone app (see HealthSample).
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_workouts_user_start", "user_id", "start_at"),
        Index(
            "ux_workouts_user_external", "user_id", "external_id", unique=True
        ),
    )


class EcgRecord(UUIDMixin, TimestampMixin, Base):
    """One electrocardiogram; the voltage CSV is stored on disk."""

    __tablename__ = "ecg_records"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    classification: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    sample_rate_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path: Mapped[str] = mapped_column(String(400))
    source: Mapped[str] = mapped_column(String(32), default="apple")

    __table_args__ = (Index("ix_ecg_user_time", "user_id", "recorded_at"),)


class RouteFile(UUIDMixin, TimestampMixin, Base):
    """One workout GPS route; the GPX file is stored on disk."""

    __tablename__ = "route_files"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    point_count: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String(400))
    source: Mapped[str] = mapped_column(String(32), default="apple")

    __table_args__ = (Index("ix_routes_user_start", "user_id", "started_at"),)


class ClinicalObservation(UUIDMixin, TimestampMixin, Base):
    """One observation parsed from the CDA clinical document."""

    __tablename__ = "clinical_observations"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(String(200))
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    effective_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(32), default="apple")

    __table_args__ = (
        Index("ix_clinical_user_time", "user_id", "effective_at"),
    )


class ClinicalDocument(UUIDMixin, TimestampMixin, Base):
    """The stored CDA file (export_cda.xml) plus a small summary."""

    __tablename__ = "clinical_documents"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    file_path: Mapped[str] = mapped_column(String(400))
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32), default="apple")

    __table_args__ = (Index("ix_cda_user", "user_id", "created_at"),)


class ImportJob(UUIDMixin, TimestampMixin, Base):
    """Progress record for one background Apple Health import."""

    __tablename__ = "import_jobs"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    phase: Mapped[str] = mapped_column(String(32), default="queued")
    processed: Mapped[int] = mapped_column(Integer, default=0)
    samples: Mapped[int] = mapped_column(Integer, default=0)
    workouts: Mapped[int] = mapped_column(Integer, default=0)
    ecg: Mapped[int] = mapped_column(Integer, default=0)
    routes: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_jobs_user_created", "user_id", "created_at"),)
