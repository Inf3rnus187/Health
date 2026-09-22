"""Medical records: uploaded documents a patient shares with a carer.

Prescriptions, imaging reports (and images), lab results, EFR, walk tests,
a French CDA file, etc. The file bytes live on disk (encrypted at rest via
the crypto layer); only metadata is stored here.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class MedicalDocument(UUIDMixin, TimestampMixin, Base):
    """One uploaded medical document with its type and date."""

    __tablename__ = "medical_documents"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32), default="autre")
    title: Mapped[str] = mapped_column(String(200))
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_path: Mapped[str] = mapped_column(String(400))
    media_type: Mapped[str] = mapped_column(
        String(100), default="application/octet-stream"
    )
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: AI reading of the document: None (never), queued, done or failed.
    analysis_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    #: Type, summary and the grounded values extracted (see document_ai).
    analysis: Mapped[dict[str, Any] | None] = mapped_column(
        JSONColumn, nullable=True
    )

    __table_args__ = (Index("ix_meddoc_user_created", "user_id", "created_at"),)


class Condition(UUIDMixin, TimestampMixin, Base):
    """A declared medical condition (maladie)."""

    __tablename__ = "conditions"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_cond_user", "user_id", "created_at"),)


class Treatment(UUIDMixin, TimestampMixin, Base):
    """A treatment / medication the patient is on (traitement)."""

    __tablename__ = "treatments"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    dose: Mapped[str | None] = mapped_column(String(80), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(80), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_treat_user", "user_id", "created_at"),)


class Appointment(UUIDMixin, TimestampMixin, Base):
    """A medical appointment (rendez-vous), manual or from .ics."""

    __tablename__ = "appointments"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    practitioner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    external_uid: Mapped[str | None] = mapped_column(String(200), nullable=True)

    __table_args__ = (Index("ix_appt_user_start", "user_id", "starts_at"),)
