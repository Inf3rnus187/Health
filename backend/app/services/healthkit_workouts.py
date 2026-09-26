"""Workouts from the iPhone app, kept by their UUID, and their days.

Stored with the native export's workouts (``HKWorkoutActivityTypeWalking``,
duration, energy, distance). A day's session count and totals
(``workout.*``) come from ONE channel — the one with the most workouts
that day — so a workout both exported and synced is never counted twice.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import Workout
from app.models.measurement import Measurement
from app.schemas.healthkit import HkWorkout
from app.schemas.measurement import MeasurementIn
from app.services import measurements
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import WORKOUT_SPECS
from app.services.healthkit_common import SOURCE, Touched, aware, chunks

_TYPE = "HKWorkoutActivityType"
_NATIVE = "watch"  # the source of the native export's daily roll-ups
#: workout.* key → the total it holds.
_TOTALS = {
    "workout.count": "count",
    "workout.total_min": "duration_min",
    "workout.energy": "energy_kcal",
    "workout.distance": "distance_km",
}


async def store(
    session: AsyncSession,
    user_id: str,
    workouts: list[HkWorkout],
    tz: ZoneInfo,
    touched: Touched,
) -> int:
    """Store the workouts: a UUID sent again replaces its workout."""
    rows = {w.uuid: _row(user_id, w, tz) for w in workouts}
    await forget(session, user_id, list(rows), touched)
    if rows:
        await session.execute(insert(Workout), list(rows.values()))
    touched.workouts.extend(row["start_at"] for row in rows.values())
    return len(rows)


async def forget(
    session: AsyncSession, user_id: str, uuids: list[str], touched: Touched
) -> int:
    """Remove the workouts with these UUIDs (their days change)."""
    count = 0
    for part in chunks(uuids):
        mine = (Workout.user_id == user_id) & Workout.external_id.in_(part)
        found = await session.execute(select(Workout.start_at).where(mine))
        starts = list(found.scalars())
        touched.workouts.extend(starts)
        count += len(starts)
        await session.execute(delete(Workout).where(mine))
    return count


async def recompute(
    session: AsyncSession, user_id: str, tz: ZoneInfo, starts: list[datetime]
) -> int:
    """Each changed day's session count and totals; the days done."""
    cache = MetricCache()
    ids = {
        spec.key: await cache.id_for(session, spec) for spec in WORKOUT_SPECS
    }
    days = sorted({_utc(at).astimezone(tz).date() for at in starts})
    for day in days:
        workouts = await _of_day(session, user_id, day, tz)
        await _write(session, user_id, day, workouts, ids)
    return len(days)


def _row(user_id: str, workout: HkWorkout, tz: ZoneInfo) -> dict[str, Any]:
    """One workout row."""
    start, end = aware(workout.start, tz), aware(workout.end, tz)
    minutes = workout.duration_min
    if minutes is None:
        minutes = max((end - start).total_seconds() / 60, 0.0)
    activity = workout.activity
    if not activity.startswith(_TYPE):
        activity = _TYPE + activity[:1].upper() + activity[1:]
    return {
        "id": new_uuid(), "user_id": user_id, "activity_type": activity,
        "start_at": start, "end_at": end, "duration_min": round(minutes, 1),
        "energy_kcal": workout.energy_kcal,
        "distance_km": workout.distance_km, "source": SOURCE,
        "external_id": workout.uuid, "created_at": utcnow(),
    }  # fmt: skip


async def _of_day(
    session: AsyncSession, user_id: str, day: date, tz: ZoneInfo
) -> list[Workout]:
    """The day's workouts from the channel that has the most of them."""
    first = datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)
    found = await session.execute(
        select(Workout).where(
            Workout.user_id == user_id,
            Workout.start_at >= first,
            Workout.start_at < first + timedelta(days=1),
        )
    )
    by: dict[str, list[Workout]] = {}
    for workout in found.scalars():
        by.setdefault(workout.source, []).append(workout)
    if not by:
        return []
    return by[max(by, key=lambda s: (len(by[s]), s == SOURCE))]


def _totals(workouts: list[Workout]) -> dict[str, float]:
    """Count and totals of a day's workouts (none: empty)."""
    if not workouts:
        return {}
    out = {"workout.count": float(len(workouts))}
    for key, field in list(_TOTALS.items())[1:]:
        values = [getattr(w, field) for w in workouts if getattr(w, field)]
        if values:
            out[key] = round(sum(values), 1)
    return out


async def _write(
    session: AsyncSession,
    user_id: str,
    day: date,
    workouts: list[Workout],
    ids: dict[str, str],
) -> None:
    """Set the day's workout.* values; those it no longer has go."""
    totals = _totals(workouts)
    gone = [ids[key] for key in _TOTALS if key not in totals]
    await session.execute(
        delete(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id.in_(gone),
            Measurement.date_key == day,
            Measurement.event_id.is_(None),
            Measurement.source.in_([SOURCE, _NATIVE]),
        )
    )
    if totals:
        source = SOURCE if workouts[0].source == SOURCE else _NATIVE
        items = [
            MeasurementIn(metric_key=key, date_key=day, value=value)
            for key, value in totals.items()
        ]
        await measurements.record_batch(session, user_id, items, source=source)


def _utc(at: datetime) -> datetime:
    """A stored time as aware UTC (SQLite gives it back naive)."""
    return at if at.tzinfo else at.replace(tzinfo=UTC)
