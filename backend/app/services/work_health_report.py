"""Build the work ↔ health PDF (report type ``work_health``)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import WorkSession
from app.services import evidence, evidence_files, work_health, work_health_pdf
from app.services.daily_rollup import user_zone
from app.services.timed_entries import utc


async def render(
    session: AsyncSession,
    user_id: str,
    period: tuple[date | None, date | None],
    contract: float,
) -> bytes:
    """The PDF over ``period`` (default: from the first session to today)."""
    last = period[1] or date.today()
    first = (
        period[0]
        or await first_day(session, user_id)
        or last - timedelta(days=364)
    )
    data = await work_health.gather(session, user_id, first, last, contract)
    images = await _images(session, user_id, data["evidence"])
    return work_health_pdf.build(data, images)


async def first_day(session: AsyncSession, user_id: str) -> date | None:
    """The local day of the first work session (None without any)."""
    anchor = func.coalesce(WorkSession.start_at, WorkSession.end_at)
    found = await session.execute(
        select(func.min(anchor)).where(WorkSession.user_id == user_id)
    )
    first = found.scalar_one_or_none()
    if first is None:
        return None
    tz = await user_zone(session, user_id)
    return utc(first).astimezone(tz).date()


async def _images(
    session: AsyncSession, user_id: str, items: list[dict[str, Any]]
) -> dict[str, bytes]:
    """The image files of the evidence (to embed in the annex)."""
    out = {}
    for item in items:
        if (item["media_type"] or "").startswith("image/"):
            row = await evidence.get(session, user_id, item["id"])
            data = evidence_files.read_file(row)
            if data:
                out[item["id"]] = data
    return out
