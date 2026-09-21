"""Ingest a Health Auto Export JSON payload.

The *Health Auto Export* iOS app POSTs a JSON body (not a multipart
file)::

    {"data": {"metrics": [
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-02-01 00:00:00 +0000", "qty": 8432}]}]}}

Each metric's points become daily measurements. Common metric names map
to the matching HealthKit identifier so they resolve to the same canonical
keys a native Apple export creates (and are auto-created when missing);
anything else auto-creates an ``apple.*`` metric on the fly.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ingest import IngestPayload, IngestResult, IngestSample
from app.services import ingest as ingest_svc
from app.services.apple_health.spec import synth_spec

#: The ingest schema caps a batch at 500 samples, so a full export is
#: chunked; each metric/day pair is recorded once (last value wins).
_CHUNK = 400

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


async def ingest(
    session: AsyncSession,
    user_id: str,
    payload: dict[str, Any],
    *,
    token_id: str | None = None,
) -> IngestResult:
    """Ingest a Health Auto Export JSON payload into measurements."""
    samples, skipped = _samples(_metrics(payload))
    recorded = 0
    for chunk in _chunks(samples):
        batch = IngestPayload(date_key=date.today(), samples=chunk)
        result = await ingest_svc.ingest(
            session, user_id, "watch", batch, token_id=token_id
        )
        recorded += result.recorded
        skipped.extend(result.skipped)
    return IngestResult(recorded=recorded, skipped=skipped)


def _chunks(samples: list[IngestSample]) -> Iterator[list[IngestSample]]:
    """Split samples into batches the ingest schema will accept."""
    for start in range(0, len(samples), _CHUNK):
        yield samples[start : start + _CHUNK]


def _metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the metric objects, tolerating a missing ``data`` wrapper."""
    data = payload.get("data")
    source = data if isinstance(data, dict) else payload
    metrics = source.get("metrics") if isinstance(source, dict) else None
    return [m for m in metrics or [] if isinstance(m, dict)]


def _samples(
    metrics: list[dict[str, Any]],
) -> tuple[list[IngestSample], list[str]]:
    """Aggregate Health Auto Export points into one sample per metric/day.

    The app exports many raw intraday points; each day is reduced by the
    metric's own hint (sum for steps/energy, average for heart rate…) so a
    daily total is a total, not the last reading.
    """
    groups: dict[tuple[str, date | None], dict[str, Any]] = {}
    skipped: list[str] = []
    for metric in metrics:
        name = str(metric.get("name") or "")
        hk_type = HAE_MAP.get(name) or name
        unit = str(metric["units"]) if metric.get("units") else None
        for point in metric.get("data") or []:
            if not _absorb(groups, hk_type, unit, point):
                skipped.append(name or "unknown")
    return [_finalize(key[0], grp) for key, grp in groups.items()], skipped


def _absorb(
    groups: dict[tuple[str, date | None], dict[str, Any]],
    hk_type: str,
    unit: str | None,
    point: Any,
) -> bool:
    """Add one metric point to its (metric, day) group; False if unusable."""
    if not isinstance(point, dict) or not hk_type:
        return False
    num = _num(point.get("qty", point.get("Avg")))
    if num is None:
        return False
    ts = _ts(point.get("date"))
    key = (hk_type, ts.date() if ts else None)
    group = groups.setdefault(key, {"values": [], "unit": unit, "ts": ts})
    group["values"].append(num)
    if ts is not None:
        group["ts"] = ts
    return True


def _finalize(hk_type: str, group: dict[str, Any]) -> IngestSample:
    """Reduce a day's points to one sample using the metric's hint."""
    agg = synth_spec(hk_type, group["unit"]).agg
    return IngestSample(
        healthkit_type=hk_type,
        value=_reduce(group["values"], agg),
        unit=group["unit"],
        ts=group["ts"],
    )


def _reduce(values: list[float], agg: str) -> float:
    """Combine a day's values by aggregation hint."""
    if agg == "sum":
        return float(sum(values))
    if agg == "min":
        return float(min(values))
    if agg == "max":
        return float(max(values))
    if agg == "avg":
        return sum(values) / len(values)
    return float(values[-1])


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
