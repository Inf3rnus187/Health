"""Import every Apple Health record into full-fidelity raw storage.

One streaming pass over ``export.xml`` bulk-inserts all samples into
``health_samples`` and workouts into ``workouts`` (millions of rows in
bounded memory), while caching a daily roll-up per metric in
``measurements`` so the dashboards stay plottable.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from typing import IO, Any, NamedTuple

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample, Workout
from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services.apple_health.accumulator import DailyAggregator
from app.services.apple_health.hk_values import category_value
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.parser import (
    Item,
    RawRecord,
    RawWorkout,
    parse_xml,
)
from app.services.apple_health.spec import (
    SLEEP_RAW,
    SLEEP_STAGE_MAP,
    SLEEP_TYPE,
    WORKOUT_ATTR,
    WORKOUT_SPECS,
    MetricSpec,
    synth_spec,
)
from app.services.apple_health.timeparse import to_dt, to_float
from app.services.apple_health.units import convert

_BATCH = 5000
_COMMIT_EVERY = 50000
_ROLLUP_BATCH = 500
_WORKOUT_CANON = {spec.key: spec.unit for spec in WORKOUT_SPECS}

Progress = Callable[[int], Awaitable[None]]


class ImportStats(NamedTuple):
    """Row counts written by one import."""

    samples: int
    workouts: int


async def run_import(
    session: AsyncSession,
    user_id: str,
    xml: IO[bytes],
    on_progress: Progress,
) -> ImportStats:
    """Stream ``export.xml`` into raw storage plus daily roll-ups."""
    items = parse_xml(xml)
    return await _RawImporter(session, user_id).run(items, on_progress)


async def run_records(
    session: AsyncSession,
    user_id: str,
    items: Iterator[Item],
    on_progress: Progress,
) -> ImportStats:
    """Import raw records from any source (e.g. CSV) into raw storage."""
    return await _RawImporter(session, user_id).run(items, on_progress)


def _sample_row(
    user_id: str, metric_id: str, rec: RawRecord, start: Any, num: float | None
) -> dict[str, Any]:
    """Build one health_samples insert row (category label kept)."""
    return {
        "id": new_uuid(),
        "user_id": user_id,
        "metric_id": metric_id,
        "start_at": start,
        "end_at": to_dt(rec.end),
        "value_num": num,
        "value_text": None if to_float(rec.value) is not None else rec.value,
        "unit": rec.unit,
        "source": "apple",
        "device": rec.device,
        "created_at": utcnow(),
    }


def _canon(wk: RawWorkout, attr: str, canon: str | None) -> float | None:
    """Convert a workout numeric attribute to its canonical unit."""
    value = to_float(wk.attrs.get(attr))
    if value is None:
        return None
    return convert(value, wk.attrs.get(f"{attr}Unit", ""), canon)


def _workout_row(user_id: str, wk: RawWorkout, start: Any) -> dict[str, Any]:
    """Build one workouts insert row."""
    return {
        "id": new_uuid(),
        "user_id": user_id,
        "activity_type": wk.activity_type,
        "start_at": start,
        "end_at": to_dt(wk.end),
        "duration_min": _canon(wk, "duration", "min"),
        "energy_kcal": _canon(wk, "totalEnergyBurned", "kcal"),
        "distance_km": _canon(wk, "totalDistance", "km"),
        "source": "apple",
        "created_at": utcnow(),
    }


class _RawImporter:
    """Streaming importer accumulating raw rows and daily roll-ups."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        """Bind the importer to a session and user."""
        self.session = session
        self.user_id = user_id
        self.cache = MetricCache()
        self.agg = DailyAggregator()
        self._specs: dict[str, MetricSpec] = {}
        self._samples: list[dict[str, Any]] = []
        self._workouts: list[dict[str, Any]] = []
        self.n_samples = 0
        self.n_workouts = 0

    async def run(
        self, items: Iterator[Item], on_progress: Progress
    ) -> ImportStats:
        """Consume raw items, then materialise the daily roll-ups."""
        processed = 0
        for kind, obj in items:
            await self._dispatch(kind, obj)
            processed += 1
            if processed % _BATCH == 0:
                await self._flush()
            if processed % _COMMIT_EVERY == 0:
                await on_progress(processed)
                await self.session.commit()
        await self._flush()
        await self.session.commit()
        await self._finalize()
        await on_progress(processed)
        await self.session.commit()
        return ImportStats(self.n_samples, self.n_workouts)

    async def _dispatch(self, kind: str, obj: Any) -> None:
        """Route one parsed item to its handler."""
        if kind == "record":
            await self._record(obj)
        else:
            await self._workout(obj)

    def _spec(self, hk_type: str, unit: str | None) -> MetricSpec:
        """Resolve a metric spec once per HealthKit type (cached)."""
        spec = self._specs.get(hk_type)
        if spec is None:
            spec = synth_spec(hk_type, unit)
            self._specs[hk_type] = spec
        return spec

    async def _record(self, rec: RawRecord) -> None:
        """Buffer a raw sample and feed its daily roll-up."""
        start = to_dt(rec.start)
        if start is None:
            return
        is_sleep = rec.hk_type == SLEEP_TYPE
        spec = SLEEP_RAW if is_sleep else self._spec(rec.hk_type, rec.unit)
        metric_id = await self.cache.id_for(self.session, spec)
        num = to_float(rec.value)
        if num is None and not is_sleep:
            num = category_value(rec.hk_type, rec.value, start, to_dt(rec.end))
        self._samples.append(
            _sample_row(self.user_id, metric_id, rec, start, num)
        )
        if is_sleep:
            self._rollup_sleep(rec, start)
        elif num is not None:
            value = convert(num, rec.unit or "", spec.unit)
            self.agg.add(spec.key, start.date(), value, spec.agg)

    def _rollup_sleep(self, rec: RawRecord, start: Any) -> None:
        """Add sleep-stage minutes to the wake-up day roll-up."""
        keys = SLEEP_STAGE_MAP.get(rec.value or "")
        end = to_dt(rec.end)
        if not keys or end is None:
            return
        minutes = (end - start).total_seconds() / 60.0
        for key in keys:
            self.agg.add(key, end.date(), minutes, "sum")

    async def _workout(self, wk: RawWorkout) -> None:
        """Buffer a workout row and feed its daily roll-ups."""
        start = to_dt(wk.start)
        if start is None:
            return
        self._workouts.append(_workout_row(self.user_id, wk, start))
        day = start.date()
        self.agg.add("workout.count", day, 1.0, "sum")
        for attr, key in WORKOUT_ATTR:
            value = _canon(wk, attr, _WORKOUT_CANON[key])
            if value is not None:
                self.agg.add(key, day, value, "sum")

    async def _flush(self) -> None:
        """Bulk-insert buffered samples and workouts (commit is separate)."""
        if self._samples:
            await self.session.execute(insert(HealthSample), self._samples)
            self.n_samples += len(self._samples)
            self._samples = []
        if self._workouts:
            await self.session.execute(insert(Workout), self._workouts)
            self.n_workouts += len(self._workouts)
            self._workouts = []

    async def _finalize(self) -> None:
        """Upsert the cached daily roll-ups into measurements."""
        for spec in WORKOUT_SPECS:
            await self.cache.id_for(self.session, spec)
        await self.session.commit()
        batch: list[MeasurementIn] = []
        for key, day, value in self.agg.results():
            batch.append(
                MeasurementIn(metric_key=key, date_key=day, value=value)
            )
            if len(batch) >= _ROLLUP_BATCH:
                await self._flush_rollups(batch)
                batch = []
        await self._flush_rollups(batch)

    async def _flush_rollups(self, batch: list[MeasurementIn]) -> None:
        """Persist one roll-up batch through the measurement upsert."""
        if not batch:
            return
        await measure.record_batch(
            self.session, self.user_id, batch, source="watch"
        )
        await self.session.commit()
