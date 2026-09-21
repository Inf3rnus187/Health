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

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ingest import IngestPayload, IngestResult, IngestSample
from app.services import ingest as ingest_svc

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
    if not samples:
        return IngestResult(recorded=0, skipped=skipped)
    batch = IngestPayload(date_key=date.today(), samples=samples)
    result = await ingest_svc.ingest(
        session, user_id, "watch", batch, token_id=token_id
    )
    return IngestResult(
        recorded=result.recorded, skipped=result.skipped + skipped
    )


def _metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the metric objects, tolerating a missing ``data`` wrapper."""
    data = payload.get("data")
    source = data if isinstance(data, dict) else payload
    metrics = source.get("metrics") if isinstance(source, dict) else None
    return [m for m in metrics or [] if isinstance(m, dict)]


def _samples(
    metrics: list[dict[str, Any]],
) -> tuple[list[IngestSample], list[str]]:
    """Flatten Health Auto Export metrics into ingest samples."""
    samples: list[IngestSample] = []
    skipped: list[str] = []
    for metric in metrics:
        name = str(metric.get("name") or "")
        hk_type = HAE_MAP.get(name) or name
        unit = metric.get("units")
        for point in metric.get("data") or []:
            sample = _sample(hk_type, unit, point)
            if sample is None:
                skipped.append(name or "unknown")
            else:
                samples.append(sample)
    return samples, skipped


def _sample(hk_type: str, unit: Any, point: Any) -> IngestSample | None:
    """Build one sample from a metric point (``qty`` or ``Avg``)."""
    if not isinstance(point, dict) or not hk_type:
        return None
    num = _num(point.get("qty", point.get("Avg")))
    if num is None:
        return None
    unit_str = str(unit) if unit else None
    return IngestSample(
        healthkit_type=hk_type,
        value=num,
        unit=unit_str,
        ts=_ts(point.get("date")),
    )


def _num(value: Any) -> float | None:
    """Coerce a numeric point value to float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _ts(raw: Any) -> datetime | None:
    """Parse the date portion of a Health Auto Export timestamp."""
    if not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d")
    except ValueError:
        return None
