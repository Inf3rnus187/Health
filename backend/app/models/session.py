"""Refresh-token sessions enabling rotation and revocation.

Each successful login opens a session; the refresh JWT carries its id
(``sid``). Refreshing rotates the session (old one revoked, new one
issued); logout revokes it. Access tokens stay stateless and short.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AuthSession(UUIDMixin, TimestampMixin, Base):
    """A server-side refresh session for one device/login."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
