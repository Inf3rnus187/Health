"""Sync from the iPhone app: HealthKit samples, sums, workouts, deletions.

One request (``POST /sync/healthkit``) carries what the app's anchored
queries found since its last sync:

* ``samples`` — discrete quantities and categories, by HealthKit UUID
  (:mod:`healthkit_samples`); sleep stages make the nights
  (:mod:`healthkit_sleep`);
* ``statistics`` — cumulative types as HealthKit adds them up
  (:mod:`healthkit_stats`);
* ``workouts`` (:mod:`healthkit_workouts`);
* ``deleted`` — UUIDs removed in the Health app.

Everything is stored under the ``healthkit`` channel, which counts as one
HealthKit channel with the native export and Health Auto Export (a day
takes one of them, never their sum). Then only the days touched are
recomputed with the one rule (:mod:`daily_rollup`); a day left without
any sample loses the value this channel had given it.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timing import Steps
from app.models.health_raw import HealthSample, Workout
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.schemas.healthkit import HealthKitSync
from app.services import (
    daily_rollup,
    healthkit_refused,
    healthkit_samples,
    healthkit_sleep,
    healthkit_stats,
    healthkit_workouts,
)
from app.services.healthkit_common import SOURCE, Touched, chunks


async def sync(
    session: AsyncSession, user_id: str, body: HealthKitSync, steps: Steps
) -> dict[str, Any]:
    """Store what the app sends, then recompute the days it touches.

    Each step is timed in ``steps`` (the route logs and audits them).
    """
    with steps.step("zone"):
        tz = await daily_rollup.user_zone(session, user_id)
    touched = Touched()
    with steps.step("deleted"):
        deleted = await _forget(session, user_id, body.deleted, touched)
    counts = await _store(session, user_id, body, (tz, touched, steps))
    with steps.step("sleep"):
        await healthkit_sleep.recompute(session, user_id, tz, touched)
    with steps.step("days"):
        days = await _days(session, user_id, tz, touched, steps)
    with steps.step("workout_days"):
        days += await healthkit_workouts.recompute(
            session, user_id, tz, touched.workouts
        )
    skipped = [
        {"type": kind, "reason": reason, "count": count}
        for (kind, reason), count in sorted(touched.skipped.items())
    ]
    return {**counts, "deleted": deleted, "days": days, "skipped": skipped}


async def _forget(
    session: AsyncSession, user_id: str, gone: list[str], touched: Touched
) -> int:
    """Remove the samples and workouts deleted in Health; how many."""
    deleted = await healthkit_samples.forget(session, user_id, gone, touched)
    return deleted + await healthkit_workouts.forget(
        session, user_id, gone, touched
    )


async def status(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """What the hub holds from the app: counts and newest per metric.

    And the lines it refused lately (:mod:`healthkit_refused`).
    """
    rows = await _per_metric(session, user_id)
    workouts = await session.execute(
        select(func.count(Workout.id), func.max(Workout.created_at)).where(
            Workout.user_id == user_id, Workout.source == SOURCE
        )
    )
    count, last_workout = workouts.one()
    stamps = [_utc(r[4]) for r in rows if r[4]]
    stamps += [_utc(last_workout)] if last_workout else []
    return {
        "last_sync_at": max(stamps) if stamps else None,
        "samples": sum(r[2] for r in rows),
        "workouts": count,
        "metrics": [
            {"key": r[0], "label": r[1], "samples": r[2], "last": _utc(r[3])}
            for r in rows
        ],
        "refused": await healthkit_refused.recent(session, user_id),
    }


async def _store(
    session: AsyncSession,
    user_id: str,
    body: HealthKitSync,
    at: tuple[ZoneInfo, Touched, Steps],
) -> dict[str, int]:
    """Store the samples, sums and workouts (each timed); how many."""
    tz, touched, steps = at
    with steps.step("samples"):
        samples = await healthkit_samples.store(
            session, user_id, body.samples, tz, touched
        )
    with steps.step("statistics"):
        statistics = await healthkit_stats.store(
            session, user_id, body.statistics, tz, touched
        )
    with steps.step("workouts"):
        workouts = await healthkit_workouts.store(
            session, user_id, body.workouts, tz, touched
        )
    return {"samples": samples, "statistics": statistics, "workouts": workouts}


async def _per_metric(session: AsyncSession, user_id: str) -> list[Any]:
    """(key, label, samples, newest start, newest arrival) per metric.

    What the app sent: the nights' totals the hub derives are left out.
    """
    found = await session.execute(
        select(
            MetricDefinition.key,
            MetricDefinition.label,
            func.count(HealthSample.id),
            func.max(HealthSample.start_at),
            func.max(HealthSample.created_at),
        )
        .join(MetricDefinition, MetricDefinition.id == HealthSample.metric_id)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.source == SOURCE,
            ~HealthSample.external_id.like(f"{healthkit_sleep.NIGHT}%"),
        )
        .group_by(MetricDefinition.key, MetricDefinition.label)
        .order_by(MetricDefinition.key)
    )
    return list(found.all())


async def _days(
    session: AsyncSession,
    user_id: str,
    tz: ZoneInfo,
    touched: Touched,
    steps: Steps,
) -> int:
    """Recompute each touched metric over the days the sync changed.

    From its first to its last changed day, not to today: a first sync
    sends years of history in requests of 5 000 samples, and each
    request recomputing from its first day to today read the whole
    history again (days after the last one received keep their samples,
    so their values). Read in the table's order, as the reconcile reads.
    A changed day left without any sample loses this channel's value.
    Each metric is timed (``days:<key>``).
    """
    total = 0
    for metric_id, instants in touched.metrics.items():
        metric = await session.get(MetricDefinition, metric_id)
        if metric is None:
            continue
        days = {_utc(at).astimezone(tz).date() for at in instants}
        span = (min(days), max(days) + timedelta(days=1))
        with steps.step(f"days:{metric.key}"):
            found = await daily_rollup.rebuild_days(
                session, user_id, metric, tz, (None, span, True)
            )
            await _clear_empty(session, user_id, metric_id, days - found)
        total += len(found)
    return total


async def _clear_empty(
    session: AsyncSession, user_id: str, metric_id: str, days: set[date]
) -> None:
    """Drop this channel's daily value of the days left without samples.

    The recompute has just read every sample of the changed days: those
    it found none for are empty (one statement, not one per day).
    """
    for part in chunks(sorted(days)):
        await session.execute(
            delete(Measurement).where(
                Measurement.user_id == user_id,
                Measurement.metric_id == metric_id,
                Measurement.date_key.in_(part),
                Measurement.event_id.is_(None),
                Measurement.source == SOURCE,
            )
        )


def _utc(at: datetime) -> datetime:
    """A stored time as aware UTC (SQLite gives it back naive)."""
    return at if at.tzinfo else at.replace(tzinfo=UTC)
