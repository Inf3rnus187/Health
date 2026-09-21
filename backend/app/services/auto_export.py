"""Ingest a Health Auto Export JSON payload.

The *Health Auto Export* iOS app POSTs a JSON body (not a multipart
file)::

    {"data": {"metrics": [
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-02-01 00:00:00 +0000", "qty": 8432}]}]}}

Like the native Apple import, every point is stored as a raw
``health_samples`` row (so it shows up in the Données browser) *and* folded
into a daily ``measurements`` roll-up (so the dashboards and home tiles
read a real daily total, aggregated by the metric's own hint — summed for
steps/energy, averaged for heart rate…). Re-pushing a day replaces that
day's Health-Auto-Export samples, so repeated syncs stay idempotent.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any, NamedTuple

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.schemas.ingest import IngestResult
from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services.apple_health.accumulator import DailyAggregator
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec, synth_spec
from app.services.apple_health.units import convert

_SOURCE = "auto-export"
_RAW_CHUNK = 2000
_ROLLUP_CHUNK = 400

#: Health Auto Export metric name -> HealthKit identifier (so it resolves
#: to the same canonical key a native Apple export would create).
HAE_MAP: dict[str, str] = {
    "step_count": "HKQuantityTypeIdentifierStepCount",
    "distance_walking_running": (
        "HKQuantityTypeIdentifierDistanceWalkingRunning"
    ),
    "flights_climbed": "HKQuantityTypeIdentifierFlightsClimbed",
    "active_energy": "HKQuantityTypeIdentifierActiveEnergyBurned",
    "basal_energy_burned": "HKQuantityTypeIdentifierBasalEnergyBurned",
    "apple_exercise_time": "HKQuantityTypeIdentifierAppleExerciseTime",
    "apple_stand_time": "HKQuantityTypeIdentifierAppleStandTime",
    "heart_rate": "HKQuantityTypeIdentifierHeartRate",
    "resting_heart_rate": "HKQuantityTypeIdentifierRestingHeartRate",
    "walking_heart_rate_average": (
        "HKQuantityTypeIdentifierWalkingHeartRateAverage"
    ),
    "heart_rate_variability": (
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
    ),
    "respiratory_rate": "HKQuantityTypeIdentifierRespiratoryRate",
    "blood_oxygen_saturation": "HKQuantityTypeIdentifierOxygenSaturation",
    "oxygen_saturation": "HKQuantityTypeIdentifierOxygenSaturation",
    "weight_body_mass": "HKQuantityTypeIdentifierBodyMass",
    "body_mass_index": "HKQuantityTypeIdentifierBodyMassIndex",
    "height": "HKQuantityTypeIdentifierHeight",
    "vo2_max": "HKQuantityTypeIdentifierVO2Max",
}


class _Raw(NamedTuple):
    """One parsed Health Auto Export point, before metric resolution."""

    hk_type: str
    unit: str | None
    ts: datetime
    value: float


class _Point(NamedTuple):
    """A parsed point with its resolved metric id and spec."""

    metric_id: str
    spec: MetricSpec
    unit: str | None
    ts: datetime
    value: float


async def ingest(
    session: AsyncSession,
    user_id: str,
    payload: dict[str, Any],
    *,
    token_id: str | None = None,
) -> IngestResult:
    """Store a Health Auto Export payload as raw samples + daily roll-ups."""
    raw, skipped = _parse(_metrics(payload))
    if not raw:
        return IngestResult(recorded=0, skipped=skipped)
    points = await _resolve(session, raw, MetricCache())
    await _store_raw(session, user_id, points)
    recorded = await _store_rollups(session, user_id, points)
    return IngestResult(recorded=recorded, skipped=skipped)


def _metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the metric objects, tolerating a missing ``data`` wrapper."""
    data = payload.get("data")
    source = data if isinstance(data, dict) else payload
    metrics = source.get("metrics") if isinstance(source, dict) else None
    return [m for m in metrics or [] if isinstance(m, dict)]


def _parse(metrics: list[dict[str, Any]]) -> tuple[list[_Raw], list[str]]:
    """Flatten metric points into raw entries; collect unusable names."""
    raw: list[_Raw] = []
    skipped: list[str] = []
    for metric in metrics:
        name = str(metric.get("name") or "")
        hk_type = HAE_MAP.get(name) or name
        unit = str(metric["units"]) if metric.get("units") else None
        for point in metric.get("data") or []:
            entry = _entry(hk_type, unit, point)
            if entry is None:
                skipped.append(name or "?")
            else:
                raw.append(entry)
    return raw, skipped


def _entry(hk_type: str, unit: str | None, point: Any) -> _Raw | None:
    """Build one raw entry from a metric point (``qty`` or ``Avg``)."""
    if not isinstance(point, dict) or not hk_type:
        return None
    num = _num(point.get("qty", point.get("Avg")))
    ts = _ts(point.get("date"))
    if num is None or ts is None:
        return None
    return _Raw(hk_type, unit, ts, num)


async def _resolve(
    session: AsyncSession, raw: list[_Raw], cache: MetricCache
) -> list[_Point]:
    """Resolve each entry's metric id + spec (creating metrics as needed)."""
    specs: dict[str, MetricSpec] = {}
    out: list[_Point] = []
    for entry in raw:
        spec = specs.get(entry.hk_type)
        if spec is None:
            spec = synth_spec(entry.hk_type, entry.unit)
            specs[entry.hk_type] = spec
        metric_id = await cache.id_for(session, spec)
        out.append(_Point(metric_id, spec, entry.unit, entry.ts, entry.value))
    return out


async def _store_raw(
    session: AsyncSession, user_id: str, points: list[_Point]
) -> None:
    """Replace each metric's covered day-range, then bulk-insert samples."""
    by_metric: dict[str, list[_Point]] = {}
    for point in points:
        by_metric.setdefault(point.metric_id, []).append(point)
    for metric_id, group in by_metric.items():
        await _clear_range(session, user_id, metric_id, group)
    rows = [_raw_row(user_id, point) for point in points]
    for start in range(0, len(rows), _RAW_CHUNK):
        chunk = rows[start : start + _RAW_CHUNK]
        await session.execute(insert(HealthSample), chunk)


async def _clear_range(
    session: AsyncSession, user_id: str, metric_id: str, group: list[_Point]
) -> None:
    """Delete this metric's Health-Auto-Export samples over the day-range."""
    lo = min(point.ts for point in group)
    hi = max(point.ts for point in group)
    floor = datetime.combine(lo.date(), time.min, tzinfo=lo.tzinfo)
    ceil = datetime.combine(hi.date(), time.min, tzinfo=hi.tzinfo) + timedelta(
        days=1
    )
    await session.execute(
        delete(HealthSample).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric_id,
            HealthSample.source == _SOURCE,
            HealthSample.start_at >= floor,
            HealthSample.start_at < ceil,
        )
    )


def _raw_row(user_id: str, point: _Point) -> dict[str, Any]:
    """Build one ``health_samples`` insert row for a point."""
    return {
        "id": new_uuid(),
        "user_id": user_id,
        "metric_id": point.metric_id,
        "start_at": point.ts,
        "end_at": None,
        "value_num": point.value,
        "value_text": None,
        "unit": point.unit,
        "source": _SOURCE,
        "device": "Health Auto Export",
        "created_at": utcnow(),
    }


async def _store_rollups(
    session: AsyncSession, user_id: str, points: list[_Point]
) -> int:
    """Fold points into daily roll-ups and upsert them into measurements."""
    agg = DailyAggregator()
    for point in points:
        value = convert(point.value, point.unit or "", point.spec.unit)
        agg.add(point.spec.key, point.ts.date(), value, point.spec.agg)
    batch = [
        MeasurementIn(metric_key=key, date_key=day, value=value)
        for key, day, value in agg.results()
    ]
    for start in range(0, len(batch), _ROLLUP_CHUNK):
        chunk = batch[start : start + _ROLLUP_CHUNK]
        await measure.record_batch(session, user_id, chunk, source=_SOURCE)
    return len(batch)


def _num(value: Any) -> float | None:
    """Coerce a numeric point value to float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _ts(raw: Any) -> datetime | None:
    """Parse a Health Auto Export timestamp to a tz-aware datetime.

    PostgreSQL ``timestamptz`` columns reject naive datetimes, so anything
    without an offset is anchored to UTC.
    """
    if not isinstance(raw, str):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    return None
