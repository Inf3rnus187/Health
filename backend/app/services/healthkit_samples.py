"""Raw HealthKit samples from the iPhone app, kept by their UUID.

A quantity (heart rate, weight, SpO2…) is stored as sent, in its unit
(HealthKit's own value: 0.97 for 97 %). A cumulative quantity (steps,
distance, energy…) is refused here: the iPhone and the watch record the
same steps, so it comes as HealthKit's sums (:mod:`healthkit_stats`).
Sleep keeps its stage (the ``HKCategoryValueSleepAnalysis`` number 0-5
or its name) for the nights (:mod:`healthkit_sleep`); another category
becomes the number the native export gives it (:mod:`hk_values`). A
UUID sent again replaces its sample; a deleted one is removed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.schemas.healthkit import HkSample
from app.services.apple_health.hk_values import category_value
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import (
    SLEEP_RAW,
    SLEEP_STAGE_MAP,
    SLEEP_TYPE,
    MetricSpec,
    synth_spec,
)
from app.services.healthkit_common import (
    CATEGORY,
    QUANTITY,
    SOURCE,
    Touched,
    aware,
    chunks,
)

_STAGE = "HKCategoryValueSleepAnalysis"
#: HKCategoryValueSleepAnalysis raw values (iOS 16+).
_SLEEP_VALUES = {
    0: f"{_STAGE}InBed",
    1: f"{_STAGE}AsleepUnspecified",
    2: f"{_STAGE}Awake",
    3: f"{_STAGE}AsleepCore",
    4: f"{_STAGE}AsleepDeep",
    5: f"{_STAGE}AsleepREM",
}
_UNKNOWN = (
    "type inconnu : HKQuantityTypeIdentifier… ou HKCategoryTypeIdentifier…"
)
_NOT_NUMBER = "valeur : un nombre"
_CUMULATIVE = "cumulé : l'envoyer dans statistics (sommes HealthKit)"
_SLEEP = "sommeil : value 0 à 5 (ou son nom) et end"
_CATEGORY = "catégorie : value = son nom HKCategoryValue…, ou end manquant"


async def store(
    session: AsyncSession,
    user_id: str,
    samples: list[HkSample],
    tz: ZoneInfo,
    touched: Touched,
) -> int:
    """Store the samples: a UUID sent again replaces its sample."""
    cache, rows = MetricCache(), {}
    for sample in samples:
        row = await _row(session, sample, tz, cache, touched)
        if row is not None:
            rows[sample.uuid] = {**row, "user_id": user_id}
    await forget(session, user_id, list(rows), touched)
    for part in chunks(list(rows.values())):
        await session.execute(insert(HealthSample), part)
    sleep = await cache.id_for(session, SLEEP_RAW)
    for row in rows.values():
        _mark(touched, row, sleep)
    return len(rows)


async def forget(
    session: AsyncSession, user_id: str, uuids: list[str], touched: Touched
) -> int:
    """Remove the samples with these UUIDs (their days change)."""
    sleep, count = await MetricCache().id_for(session, SLEEP_RAW), 0
    for part in chunks(uuids):
        mine = (HealthSample.user_id == user_id) & (
            HealthSample.external_id.in_(part)
        )
        found = await session.execute(
            select(
                HealthSample.metric_id,
                HealthSample.start_at,
                HealthSample.end_at,
                HealthSample.value_num,
            ).where(mine)
        )
        for row in found.mappings():
            _mark(touched, dict(row), sleep)
            count += 1
        await session.execute(delete(HealthSample).where(mine))
    return count


def _mark(touched: Touched, row: dict[str, Any], sleep: str) -> None:
    """A sample's night, or its metric's day, changes."""
    if row["metric_id"] == sleep:
        touched.nights.append(row["end_at"] or row["start_at"])
    elif row["value_num"] is not None:
        touched.metric(row["metric_id"], row["start_at"])


async def _row(
    session: AsyncSession,
    sample: HkSample,
    tz: ZoneInfo,
    cache: MetricCache,
    touched: Touched,
) -> dict[str, Any] | None:
    """The row of one sample, or None (counted in ``skipped``)."""
    spec = _spec(sample)
    if spec is None:
        touched.skip(sample.type, _UNKNOWN)
        return None
    start = aware(sample.start, tz)
    end = aware(sample.end, tz) if sample.end else None
    value = _value(sample, spec, start, end)
    if isinstance(value, str):
        touched.skip(sample.type, value)
        return None
    return {
        "id": new_uuid(), "metric_id": await cache.id_for(session, spec),
        "start_at": start, "end_at": end, "value_num": value[0],
        "value_text": value[1], "unit": sample.unit, "source": SOURCE,
        "device": sample.device, "external_id": sample.uuid,
        "created_at": utcnow(),
    }  # fmt: skip


def _spec(sample: HkSample) -> MetricSpec | None:
    """The metric a sample goes to (None: not a HealthKit type)."""
    if sample.type == SLEEP_TYPE:
        return SLEEP_RAW
    if sample.type.startswith((QUANTITY, CATEGORY)):
        return synth_spec(sample.type, sample.unit)
    return None


def _value(
    sample: HkSample,
    spec: MetricSpec,
    start: datetime,
    end: datetime | None,
) -> tuple[float | None, str | None] | str:
    """(number, text) of a sample, or why it is refused."""
    if sample.type == SLEEP_TYPE:
        return _stage(sample.value, end)
    if sample.type.startswith(QUANTITY):
        if not isinstance(sample.value, float | int):
            return _NOT_NUMBER
        if spec.agg == "sum":
            return _CUMULATIVE
        return float(sample.value), None
    text = sample.value if isinstance(sample.value, str) else None
    number = category_value(sample.type, text, start, end)
    return (number, text) if number is not None else _CATEGORY


def _stage(
    value: float | str | None, end: datetime | None
) -> tuple[float | None, str | None] | str:
    """A sleep sample's stage name (value_text), or why it is refused."""
    name = value if isinstance(value, str) else None
    if isinstance(value, float | int) and float(value).is_integer():
        name = _SLEEP_VALUES.get(int(value))
    if end is None or name not in SLEEP_STAGE_MAP:
        return _SLEEP
    return None, name
