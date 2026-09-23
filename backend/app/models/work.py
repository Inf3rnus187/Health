"""Work hours as health data: sessions, absences (sick leave), evidence."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkSession(UUIDMixin, TimestampMixin, Base):
    """One stretch at work: clocked in, then out (open while at work)."""

    __tablename__ = "work_sessions"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    #: None when the clock-in is missing (a departure logged alone).
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: None while at work, or when the clock-out is missing.
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: tap (one-tap / GPS shortcut), manual (web, assistant), import, or
    #: edited (times completed or fixed by hand).
    source: Mapped[str] = mapped_column(String(16), default="manual")
    note: Mapped[str] = mapped_column(String(200), default="")

    __table_args__ = (
        Index("uq_work_user_start", "user_id", "start_at", unique=True),
    )


class Absence(UUIDMixin, TimestampMixin, Base):
    """A period off work: sick leave, work accident, holidays, other."""

    __tablename__ = "absences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    #: arret_maladie, accident_travail, maladie_pro, conge or autre.
    kind: Mapped[str] = mapped_column(String(24), default="arret_maladie")
    cause: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (Index("ix_absences_user_start", "user_id", "start_date"),)


class Evidence(UUIDMixin, TimestampMixin, Base):
    """A proof: call, message, mail, screenshot, note (file optional)."""

    __tablename__ = "evidence"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    #: appel, sms, mail, capture, note, document or autre.
    kind: Mapped[str] = mapped_column(String(16), default="capture")
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    #: How many events it stands for (e.g. 12 calls on one screenshot).
    count: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str | None] = mapped_column(String(400), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    #: SHA-256 of the file as received (integrity in the report).
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    absence_id: Mapped[str | None] = mapped_column(
        ForeignKey("absences.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (Index("ix_evidence_user_at", "user_id", "occurred_at"),)
