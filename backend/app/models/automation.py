"""Capture/ingest automations (NFC, shortcut, schedule) — Phase 8."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class Automation(UUIDMixin, TimestampMixin, Base):
    """A named trigger→action rule owned by a user."""

    __tablename__ = "automations"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    trigger: Mapped[str] = mapped_column(String(16))
    action: Mapped[dict[str, Any]] = mapped_column(JSONColumn, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
