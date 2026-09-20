"""Apple Health import: aggregation, unit conversion and idempotency."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.db import SessionFactory
from app.models.user import User
from app.services.apple_health.importer import run_import
from app.services.apple_health.parser import parse
from app.services.apple_health.units import convert
from httpx import AsyncClient
from sqlalchemy import select

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
MEAS = "/api/v1/measurements"

_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<!DOCTYPE HealthData [\n"
    "<!ELEMENT HealthData (Record*, Workout*)>\n"
    "]>\n"
    '<HealthData locale="fr_FR">\n'
)


def _rec(rtype: str, value: str, start: str, unit: str = "count") -> str:
    end = start
    return (
        f'<Record type="{rtype}" unit="{unit}" value="{value}" '
        f'startDate="{start}" endDate="{end}"/>\n'
    )


def _quantities() -> str:
    day = "2026-01-15 08:00:00 +0000"
    step = "HKQuantityTypeIdentifierStepCount"
    heart = "HKQuantityTypeIdentifierHeartRate"
    return (
        _rec(step, "10", day)
        + _rec(step, "5", day)
        + _rec(heart, "60", day, "count/min")
        + _rec(heart, "80", day, "count/min")
        + _rec(heart, "100", day, "count/min")
        + _rec("HKQuantityTypeIdentifierBodyMass", "86.4", day, "kg")
        + _rec("HKQuantityTypeIdentifierBodyMass", "86.0", day, "kg")
        + _rec("HKQuantityTypeIdentifierOxygenSaturation", "0.97", day, "%")
        + _rec("HKQuantityTypeIdentifierDistanceWalkingRunning", "2", day, "mi")
    )


def _sleep_and_workout() -> str:
    deep = (
        '<Record type="HKCategoryTypeIdentifierSleepAnalysis" '
        'value="HKCategoryValueSleepAnalysisAsleepDeep" '
        'startDate="2026-01-14 23:50:00 +0000" '
        'endDate="2026-01-15 00:20:00 +0000"/>\n'
    )
    workout = (
        '<Workout workoutActivityType="HKWorkoutActivityTypeRunning" '
        'duration="45" durationUnit="min" '
        'totalEnergyBurned="300" totalEnergyBurnedUnit="kcal" '
        'totalDistance="5" totalDistanceUnit="km" '
        'startDate="2026-01-15 18:00:00 +0000" '
        'endDate="2026-01-15 18:45:00 +0000"/>\n'
    )
    return deep + workout


def _write_export(tmp_path: Path) -> str:
    body = _HEADER + _quantities() + _sleep_and_workout() + "</HealthData>\n"
    path = tmp_path / "export.xml"
    path.write_text(body, encoding="utf-8")
    return str(path)


async def _admin_id() -> str:
    async with SessionFactory() as session:
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        return result.scalar_one().id


async def _value(client: AsyncClient, auth: dict[str, str], key: str) -> float:
    listed = await client.get(MEAS, params={"metric_key": key}, headers=auth)
    rows = listed.json()
    assert len(rows) == 1
    return float(rows[0]["value"])


def test_unit_conversion() -> None:
    assert convert(2.0, "mi", "km") == 2.0 * 1.609344
    assert convert(0.97, "%", "%") == 97.0
    assert convert(212.0, "degF", "°C") == 100.0
    assert convert(5.0, "km", "km") == 5.0


def test_parser_skips_unknown_and_malformed(tmp_path: Path) -> None:
    day = "2026-02-01 08:00:00 +0000"
    body = (
        _HEADER
        + _rec("HKQuantityTypeIdentifierUnknownThing", "1", day)
        + _rec("HKQuantityTypeIdentifierStepCount", "abc", day)
        + '<Record type="HKQuantityTypeIdentifierStepCount" value="9"/>\n'
        + '<ActivitySummary dateComponents="2026-02-01"/>\n'
        + "</HealthData>\n"
    )
    path = tmp_path / "partial.xml"
    path.write_text(body, encoding="utf-8")
    assert list(parse(str(path))) == []


async def test_import_aggregates_daily(
    tmp_path: Path, client: AsyncClient, auth: dict[str, str]
) -> None:
    path = _write_export(tmp_path)
    user_id = await _admin_id()
    async with SessionFactory() as session:
        summary = await run_import(session, user_id, path)
    assert summary.rows > 0
    assert await _value(client, auth, "activity.steps") == 15.0
    assert await _value(client, auth, "heart.rate_avg") == 80.0
    assert await _value(client, auth, "heart.rate_min") == 60.0
    assert await _value(client, auth, "heart.rate_max") == 100.0
    assert await _value(client, auth, "body.weight") == 86.0
    assert await _value(client, auth, "body.spo2_avg") == 97.0


async def test_import_sleep_and_workout(
    tmp_path: Path, client: AsyncClient, auth: dict[str, str]
) -> None:
    path = _write_export(tmp_path)
    user_id = await _admin_id()
    async with SessionFactory() as session:
        await run_import(session, user_id, path)
    assert await _value(client, auth, "sleep.deep") == 30.0
    assert await _value(client, auth, "sleep.asleep") == 30.0
    assert await _value(client, auth, "workout.count") == 1.0
    assert await _value(client, auth, "workout.total_min") == 45.0
    assert await _value(client, auth, "activity.distance") == 2 * 1.609344


async def test_import_is_idempotent(
    tmp_path: Path, client: AsyncClient, auth: dict[str, str]
) -> None:
    path = _write_export(tmp_path)
    user_id = await _admin_id()
    async with SessionFactory() as session:
        await run_import(session, user_id, path)
    async with SessionFactory() as session:
        again = await run_import(session, user_id, path)
    assert again.metrics_added == 0
    assert await _value(client, auth, "activity.steps") == 15.0
