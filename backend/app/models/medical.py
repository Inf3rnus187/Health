"""Medical records: uploaded documents a patient shares with a carer.

Prescriptions, imaging reports (and images), lab results, EFR, walk tests,
a French CDA file, etc. The file bytes live on disk (encrypted at rest via
the crypto layer); only metadata is stored here.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


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

    __table_args__ = (Index("ix_meddoc_user_created", "user_id", "created_at"),)
