"""The metric definitions a session already read, kept for that session.

A page asks for the same metrics many times (the home page: one per
tile; « À compléter »: the sleep and steps metrics for every day). They
are read once per session (one request) and kept in ``session.info``;
a rollback, or deleting metrics, makes the session read them again.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

_KEY = "metrics_seen"


def seen(session: AsyncSession) -> dict[str, Any]:
    """The session's metrics already read, by key."""
    found: dict[str, Any] = session.info.setdefault(_KEY, {})
    return found


@event.listens_for(Session, "after_rollback")
def forget(session: Session | AsyncSession) -> None:
    """Read the metrics again (after a rollback, or deleting metrics)."""
    session.info.pop(_KEY, None)
