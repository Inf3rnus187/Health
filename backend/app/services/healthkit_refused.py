"""Lines the iPhone app sent that the hub refused, lately.

Each sync records in ``audit_log`` what it stored and what it refused
(``skipped``: type, reason, count — never a value). The app's status
(``GET /sync/healthkit``, web: Import › App iPhone) adds the refusals up
over the last ``SYNC_REFUSED_DAYS`` days: anything sent and left out
shows there. A sync recorded before refusals were (1 October 2026) is
counted apart, never taken for « none refused ».
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit import AuditLog
from app.models.base import as_utc, utcnow


async def recent(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """The lines refused over the last ``SYNC_REFUSED_DAYS`` days.

    ``days``, ``syncs``, ``checked`` (the syncs that recorded refusals),
    ``lines`` refused, and per type and reason their ``count`` and
    ``last`` time, the most refused first.
    """
    days = get_settings().sync_refused_days
    syncs, checked = 0, 0
    kinds: dict[tuple[str, str], dict[str, Any]] = {}
    for at, payload in await _syncs(session, user_id, days):
        syncs += 1
        skipped = (payload or {}).get("skipped")
        if skipped is None:  # recorded before refusals were
            continue
        checked += 1
        for line in skipped:
            _add(kinds, line, at)
    found = sorted(kinds.values(), key=lambda k: (-k["count"], k["type"]))
    return {
        "days": days,
        "syncs": syncs,
        "checked": checked,
        "lines": sum(kind["count"] for kind in found),
        "kinds": found,
    }


async def _syncs(session: AsyncSession, user_id: str, days: int) -> list[Any]:
    """The account's syncs of the last ``days``: (UTC time, payload)."""
    rows = await session.execute(
        select(AuditLog.created_at, AuditLog.payload).where(
            AuditLog.user_id == user_id,
            AuditLog.action == "sync",
            AuditLog.entity == "healthkit",
            AuditLog.created_at >= utcnow() - timedelta(days=days),
        )
    )
    return [(as_utc(at), payload) for at, payload in rows.all()]


def _add(
    kinds: dict[tuple[str, str], dict[str, Any]],
    line: dict[str, Any],
    at: datetime,
) -> None:
    """Count one refused kind of line of a sync."""
    key = (str(line.get("type")), str(line.get("reason")))
    kind = kinds.setdefault(
        key, {"type": key[0], "reason": key[1], "count": 0, "last": at}
    )
    kind["count"] += int(line.get("count") or 0)
    kind["last"] = max(kind["last"], at)
