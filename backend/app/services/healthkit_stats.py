"""Cumulative HealthKit types from the iPhone app: HealthKit's own sums.

Steps, distance, energy, flights… are recorded by the iPhone AND the
watch; HealthKit's statistics (``HKStatisticsCollectionQuery``,
``.cumulativeSum``) count them once. Each sum is a sample over its
interval (an hour is the right size). A batch replaces the sums it
overlaps for that type — a day sent again, or by hour after by day, is
never added twice.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.schemas.healthkit import HkStatistic
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import synth_spec
from app.services.healthkit_common import QUANTITY, SOURCE, Touched, aware

PREFIX = "stat:"
DEVICE = "Statistiques HealthKit"
_DISCRETE = "ponctuel : l'envoyer dans samples"
_EMPTY = "intervalle vide : end doit suivre start"


async def store(
    session: AsyncSession,
    user_id: str,
    stats: list[HkStatistic],
    tz: ZoneInfo,
    touched: Touched,
) -> int:
    """Store the sums, replacing those they overlap (per type)."""
    cache = MetricCache()
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for stat in stats:
        row = await _row(session, stat, tz, cache, touched)
        if row is not None:
            row["user_id"] = user_id
            groups.setdefault(row["metric_id"], {})[row["external_id"]] = row
    for metric_id, rows in groups.items():
        old = await _replace(session, user_id, metric_id, list(rows.values()))
        for at in [*old, *(row["start_at"] for row in rows.values())]:
            touched.metric(metric_id, at)
    return sum(len(rows) for rows in groups.values())


async def _replace(
    session: AsyncSession,
    user_id: str,
    metric_id: str,
    rows: list[dict[str, Any]],
) -> list[datetime]:
    """Replace the type's sums over the span of ``rows``; the old starts."""
    low = min(row["start_at"] for row in rows)
    high = max(row["end_at"] for row in rows)
    old = (
        (HealthSample.user_id == user_id)
        & (HealthSample.metric_id == metric_id)
        & (HealthSample.source == SOURCE)
        & HealthSample.external_id.like(f"{PREFIX}%")
        & (HealthSample.start_at < high)
        & (HealthSample.end_at > low)
    )
    found = await session.execute(select(HealthSample.start_at).where(old))
    starts = list(found.scalars())
    await session.execute(delete(HealthSample).where(old))
    await session.execute(insert(HealthSample), rows)
    return starts


async def _row(
    session: AsyncSession,
    stat: HkStatistic,
    tz: ZoneInfo,
    cache: MetricCache,
    touched: Touched,
) -> dict[str, Any] | None:
    """The row of one sum, or None (counted in ``skipped``)."""
    spec = synth_spec(stat.type, stat.unit)
    start, end = aware(stat.start, tz), aware(stat.end, tz)
    reason = _refused(stat, spec.agg, start, end)
    if reason:
        touched.skip(stat.type, reason)
        return None
    return {
        "id": new_uuid(), "metric_id": await cache.id_for(session, spec),
        "start_at": start, "end_at": end, "value_num": stat.sum,
        "value_text": None, "unit": stat.unit, "source": SOURCE,
        "device": DEVICE, "external_id": _key(stat.type, start, end),
        "created_at": utcnow(),
    }  # fmt: skip


def _refused(
    stat: HkStatistic, agg: str, start: datetime, end: datetime
) -> str:
    """Why a sum is refused ("" when it is fine)."""
    if not stat.type.startswith(QUANTITY) or agg != "sum":
        return _DISCRETE
    return _EMPTY if end <= start else ""


def _key(kind: str, start: datetime, end: datetime) -> str:
    """One id per type and interval (the same hour sent again)."""
    raw = f"{kind}|{start.isoformat()}|{end.isoformat()}".encode()
    return PREFIX + hashlib.sha256(raw).hexdigest()[:40]
