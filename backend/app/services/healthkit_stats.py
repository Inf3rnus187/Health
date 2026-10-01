"""Cumulative HealthKit types from the iPhone app: HealthKit's own sums.

Steps, distance, energy, flights… are recorded by the iPhone AND the
watch; HealthKit's statistics (``HKStatisticsCollectionQuery``,
``.cumulativeSum``) count them once. Each sum is a sample over its
interval (an hour is the right size). A batch replaces the sums it
overlaps for that type — a day sent again, or by hour after by day, is
never added twice — except those stored exactly as sent, which stay.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timing import Steps
from app.models.base import new_uuid, utcnow
from app.models.health_raw import STATS_ONLY, STATS_PREFIX, HealthSample
from app.schemas.healthkit import HkStatistic
from app.services import sample_writes
from app.services.apple_health.spec import synth_spec
from app.services.healthkit_common import (
    QUANTITY,
    SOURCE,
    Touched,
    aware,
    chunks,
)

PREFIX = STATS_PREFIX
DEVICE = "Statistiques HealthKit"
_DISCRETE = "ponctuel : l'envoyer dans samples"
_EMPTY = "intervalle vide : end doit suivre start"


async def store(
    session: AsyncSession,
    user_id: str,
    stats: list[HkStatistic],
    tz: ZoneInfo,
    at: tuple[Touched, Steps],
) -> int:
    """Store the sums, replacing those they overlap (per type).

    A sum already stored exactly as sent (same type, interval, value and
    unit) stays as it is: the app sends today's hours again at each sync,
    and only the hour still counting changes. Only the others are
    deleted and written — in one statement each, for every type — and
    only their days are recomputed. The same sums as replacing them all.
    """
    touched, steps = at
    groups = await _groups(session, user_id, stats, tz, touched)
    if not groups:
        return 0
    with steps.step("statistics:read"):
        found = await stored(session, user_id, groups)
    gone, new = _changes(groups, found)
    with steps.step("statistics:delete"):
        for part in chunks([row.id for row in gone]):
            await session.execute(
                delete(HealthSample).where(HealthSample.id.in_(part))
            )
    with steps.step("statistics:write"):
        await sample_writes.write(session, new)
    for row in gone:
        touched.metric(row.metric_id, row.start_at)
    for sent in new:
        touched.metric(sent["metric_id"], sent["start_at"])
    return sum(len(rows) for rows in groups.values())


async def _groups(
    session: AsyncSession,
    user_id: str,
    stats: list[HkStatistic],
    tz: ZoneInfo,
    touched: Touched,
) -> dict[str, dict[str, dict[str, Any]]]:
    """The sums accepted, per metric then ``external_id``.

    The refused ones are counted first; the metrics of the others are
    then looked up in one query.
    """
    kept = []
    for stat in stats:
        spec = synth_spec(stat.type, stat.unit)
        start, end = aware(stat.start, tz), aware(stat.end, tz)
        reason = _refused(stat, spec.agg, start, end)
        if reason:
            touched.skip(stat.type, reason)
        else:
            kept.append((stat, spec, start, end))
    await touched.cache.preload(session, [spec for _, spec, _, _ in kept])
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for stat, spec, start, end in kept:
        metric_id = await touched.cache.id_for(session, spec)
        row = _row(stat, (start, end), metric_id, user_id)
        groups.setdefault(metric_id, {})[row["external_id"]] = row
    return groups


async def stored(
    session: AsyncSession,
    user_id: str,
    groups: dict[str, dict[str, dict[str, Any]]],
) -> list[Any]:
    """The sums stored over each type's span of this batch.

    One statement, one branch per type (``UNION ALL``): each branch
    reads the partial index of the sums by type and end, as a query per
    type did — never the account's whole history of sums.
    """
    branches = [
        select(
            HealthSample.id,
            HealthSample.metric_id,
            HealthSample.external_id,
            HealthSample.start_at,
            HealthSample.value_num,
            HealthSample.unit,
        ).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric_id,
            HealthSample.source == SOURCE,
            # Written as is (not a parameter): the partial index applies.
            text(STATS_ONLY),
            HealthSample.start_at < max(r["end_at"] for r in rows.values()),
            HealthSample.end_at > min(r["start_at"] for r in rows.values()),
        )
        for metric_id, rows in groups.items()
    ]
    found = await session.execute(union_all(*branches))
    return list(found.all())


def _changes(
    groups: dict[str, dict[str, dict[str, Any]]], stored: list[Any]
) -> tuple[list[Any], list[dict[str, Any]]]:
    """The stored sums to delete, and the sums to write.

    A stored sum the batch sends again unchanged is neither: it stays.
    """
    new = {key: row for rows in groups.values() for key, row in rows.items()}
    gone = []
    for old in stored:
        sent = new.get(old.external_id)
        if sent is not None and (
            sent["metric_id"],
            sent["value_num"],
            sent["unit"],
        ) == (old.metric_id, old.value_num, old.unit):
            del new[old.external_id]
        else:
            gone.append(old)
    return gone, list(new.values())


def _row(
    stat: HkStatistic,
    span: tuple[datetime, datetime],
    metric_id: str,
    user_id: str,
) -> dict[str, Any]:
    """The row of one accepted sum."""
    start, end = span
    return {
        "id": new_uuid(), "user_id": user_id, "metric_id": metric_id,
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
