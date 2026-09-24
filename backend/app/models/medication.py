"""Medication intakes: each dose taken (or not), when, and how it came in.

The proof that a treatment is followed: one row per dose, at the time it
was taken, with the time it was entered (``created_at``) and the channel
(web page, iPhone Shortcut, MCP, API) — a dose typed days later shows as
such. A deleted treatment keeps its intakes (its name and dose are
copied on each one).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class MedicationIntake(UUIDMixin, TimestampMixin, Base):
    """One dose of a treatment: taken, or explicitly not taken."""

    __tablename__ = "medication_intakes"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    treatment_id: Mapped[str | None] = mapped_column(
        ForeignKey("treatments.id", ondelete="SET NULL"), nullable=True
    )
    #: The treatment's name and dose at the time (kept if it is deleted).
    name: Mapped[str] = mapped_column(String(200))
    dose: Mapped[str] = mapped_column(String(80), default="")
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_key: Mapped[date] = mapped_column(Date)
    #: ``taken``, or ``skipped`` (not taken: forgotten, refused…).
    status: Mapped[str] = mapped_column(String(12), default="taken")
    #: How it was entered: web, raccourci, mcp or api.
    source: Mapped[str] = mapped_column(String(20), default="web")
    token_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        Index("ix_intake_user_day", "user_id", "date_key"),
        Index("ix_intake_treatment", "treatment_id", "taken_at"),
    )
