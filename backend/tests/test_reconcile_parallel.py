"""Several metrics rebuilt at once: the same days as one after the other."""

from __future__ import annotations

import asyncio
import os
import sys
from asyncio.subprocess import PIPE, Process
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from app.cli import rollup_worker
from app.core.config import get_settings
from app.core.db import SessionFactory, engine
from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.models.sample_counts import counts
from app.models.user import User
from app.services import (
    daily_rollup,
    reconcile,
    reconcile_parallel,
    sample_counts,
)
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import QUANTITY_SPECS
from sqlalchemy import delete, select, update

#: HealthKit type → (unit, samples): the largest first once ranked.
_METRICS = {
    "HKQuantityTypeIdentifierHeartRate": ("count/min", 60),
    "HKQuantityTypeIdentifierActiveEnergyBurned": ("kcal", 40),
    "HKQuantityTypeIdentifierStepCount": ("count", 30),
    "HKQuantityTypeIdentifierBodyMass": ("kg", 10),
}


async def _user(email: str) -> str:
    async with SessionFactory() as session:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one()
        return user.id


async def _seed(user_id: str) -> None:
    """Samples of four metrics over a few days, in two HealthKit channels."""
    start = datetime(2026, 3, 1, 5, 0, tzinfo=UTC)
    async with SessionFactory() as session:
        for kind, (unit, n) in _METRICS.items():
            metric_id = await MetricCache().id_for(
                session, QUANTITY_SPECS[kind]
            )
            for i in range(n):
                session.add(
                    HealthSample(
                        id=new_uuid(),
                        user_id=user_id,
                        metric_id=metric_id,
                        start_at=start + timedelta(hours=7 * i),
                        value_num=0.1 * i + 70.3,
                        unit=unit,
                        source="apple" if i % 3 else "auto-export",
                        created_at=utcnow(),
                    )
                )
        await session.commit()


async def _days(user_id: str) -> list[tuple[Any, ...]]:
    """The user's daily rows, sorted: what the pages show."""
    async with SessionFactory() as session:
        rows = await session.execute(
            select(
                Measurement.metric_id,
                Measurement.date_key,
                Measurement.source,
                Measurement.value_num,
                Measurement.recorded_at,
            )
            .where(Measurement.user_id == user_id)
            .order_by(Measurement.metric_id, Measurement.date_key)
        )
        return [tuple(row) for row in rows.all()]


async def _wipe(user_id: str) -> None:
    async with SessionFactory() as session:
        await session.execute(
            delete(Measurement).where(Measurement.user_id == user_id)
        )
        await session.commit()


async def _reconcile(user_id: str) -> dict[str, Any]:
    async with SessionFactory() as session:
        return await reconcile.run(session, user_id)


async def test_parallel_writes_the_same_days(
    monkeypatch: pytest.MonkeyPatch, member: dict[str, str]
) -> None:
    """3 processes or 1: the same rows, and only the user's own."""
    admin = await _user(get_settings().admin_email)
    other = await _user("membre@example.com")
    await _seed(admin)
    await _seed(other)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 1)
    one_by_one = await _reconcile(admin)
    expected = await _days(admin)
    assert one_by_one["metrics"] == 4 and len(expected) == one_by_one["days"]
    await _wipe(admin)

    used: list[int] = []
    real = reconcile_parallel.rebuild

    async def spy(*args: Any) -> list[reconcile_parallel.Spent]:
        used.append(len(args[0]))  # the processes it was given
        return await real(*args)

    monkeypatch.setattr(reconcile_parallel, "rebuild", spy)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 3)
    at_once = await _reconcile(admin)
    assert used == [3]
    assert await _days(admin) == expected
    assert at_once["days"] == one_by_one["days"]
    assert len(at_once["slowest"]) == 4
    assert await _days(other) == []  # the other account is not touched


async def test_largest_metrics_start_first() -> None:
    """Ranked by samples, so a long metric never starts last."""
    admin = await _user(get_settings().admin_email)
    await _seed(admin)
    async with SessionFactory() as session:
        metrics = await reconcile._sampled(session, admin)
        order = await reconcile_parallel.pieces(
            session, admin, metrics, ZoneInfo("UTC"), 4
        )
    keys = {m.id: m.key for m in metrics}
    assert [(keys[p.metric_id], p.span) for p in order] == [
        ("heart.rate", None),  # 60 samples: under the least to cut
        ("activity.active_energy", None),
        ("activity.steps", None),
        ("body.weight", None),
    ]


async def test_a_large_metric_is_cut_into_periods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cut at local midnights, the parts first: the same days written."""
    admin = await _user(get_settings().admin_email)
    await _seed(admin)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 1)
    await _reconcile(admin)
    expected = await _days(admin)
    await _wipe(admin)
    monkeypatch.setattr(get_settings(), "reconcile_split_min_samples", 10)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 3)
    report = await _reconcile(admin)
    assert await _days(admin) == expected
    assert report["days"] == len(expected)
    parts = [s for s in report["slowest"] if s.startswith("heart.rate ")]
    assert {p.split()[1] for p in parts} == {"1/2", "2/2"}  # 60 of 140


async def test_periods_cut_across_a_change_of_time() -> None:
    """Two periods give every day once, whatever the clocks did."""
    admin = await _user(get_settings().admin_email)
    tz = ZoneInfo("Europe/Paris")
    start = datetime(2026, 3, 27, 21, 10, tzinfo=UTC)
    spec = QUANTITY_SPECS["HKQuantityTypeIdentifierStepCount"]
    async with SessionFactory() as session:
        metric_id = await MetricCache().id_for(session, spec)
        for i in range(24 * 6):  # every 30 min over the night of 29 March
            session.add(
                HealthSample(
                    id=new_uuid(),
                    user_id=admin,
                    metric_id=metric_id,
                    start_at=start + timedelta(minutes=30 * i),
                    value_num=10.1 + i,
                    unit="count",
                    source="apple",
                    created_at=utcnow(),
                )
            )
        await session.commit()
        metric = await session.get(MetricDefinition, metric_id)
    assert metric is not None
    whole = await _rollup(admin, metric, tz, [None])
    for cut in (date(2026, 3, 29), date(2026, 3, 30)):
        assert (
            await _rollup(admin, metric, tz, [(None, cut), (cut, None)])
            == whole
        )


async def _rollup(
    user_id: str, metric: MetricDefinition, tz: ZoneInfo, spans: list[Any]
) -> list[tuple[Any, ...]]:
    """The days written by rebuilding these spans, from none."""
    await _wipe(user_id)
    async with SessionFactory() as session:
        for span in spans:
            await daily_rollup.rebuild(session, user_id, metric, tz, span=span)
        await session.commit()
    return await _days(user_id)


async def test_more_processes_than_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """8 processes for 4 metrics: the same days, every process ends."""
    admin = await _user(get_settings().admin_email)
    await _seed(admin)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 1)
    await _reconcile(admin)
    expected = await _days(admin)
    await _wipe(admin)
    ended: list[int | None] = []
    real = reconcile_parallel.started

    @asynccontextmanager
    async def spy(*args: Any) -> AsyncIterator[list[Process]]:
        async with real(*args) as workers:
            yield workers
        ended.extend(worker.returncode for worker in workers)

    monkeypatch.setattr(reconcile_parallel, "started", spy)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 8)
    await _reconcile(admin)
    assert await _days(admin) == expected
    assert ended == [0] * 8


async def test_accounts_reconciled_together_take_the_cores_in_turn(
    monkeypatch: pytest.MonkeyPatch, member: dict[str, str]
) -> None:
    """Two accounts at once: one set of processes at a time, both right."""
    accounts = [
        await _user(get_settings().admin_email),
        await _user("membre@example.com"),
    ]
    for user_id in accounts:
        await _seed(user_id)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 1)
    expected = []
    for user_id in accounts:
        await _reconcile(user_id)
        expected.append(await _days(user_id))
        await _wipe(user_id)
    active, peak = [0], [0]
    real = reconcile_parallel.started

    @asynccontextmanager
    async def spy(*args: Any) -> AsyncIterator[list[Process]]:
        async with real(*args) as workers:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
            await asyncio.sleep(0.3)  # the other account tries meanwhile
            try:
                yield workers
            finally:
                active[0] -= 1

    monkeypatch.setattr(reconcile_parallel, "started", spy)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 2)
    await asyncio.gather(*(_reconcile(user_id) for user_id in accounts))
    assert [await _days(user_id) for user_id in accounts] == expected
    assert peak == [1]


async def test_counts_rebuilt_while_days_are_computed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The raw counts are still checked and made exact, meanwhile."""
    admin = await _user(get_settings().admin_email)
    await _seed(admin)
    async with SessionFactory() as session:
        truth = sorted(await sample_counts.of_user(session, admin))
        await session.execute(update(counts).values(n=999))
        await session.commit()
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 2)
    await _reconcile(admin)
    async with SessionFactory() as session:
        assert sorted(await sample_counts.of_user(session, admin)) == truth


async def test_one_metric_starts_no_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = await _user(get_settings().admin_email)
    async with SessionFactory() as session:
        await reconcile.run(session, admin)  # no sample at all
        assert await reconcile._processes(session, admin) == 0
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 4)
    await _seed(admin)
    async with SessionFactory() as session:
        assert await reconcile._processes(session, admin) == 4


async def test_a_metric_removed_meanwhile_writes_nothing() -> None:
    admin = await _user(get_settings().admin_email)
    owner = (admin, new_uuid())
    spent = await rollup_worker._one(engine, owner, None, ZoneInfo("UTC"))
    assert spent[2] == 0


async def test_started_from_a_script_on_python_input() -> None:
    """The processes do not depend on how the reconcile was started."""
    admin = await _user(get_settings().admin_email)
    await _seed(admin)
    script = (
        "import asyncio, sys\n"
        "from app.core.db import SessionFactory\n"
        "from app.services import reconcile\n"
        "async def main():\n"
        "    async with SessionFactory() as session:\n"
        "        report = await reconcile.run(session, sys.argv[1])\n"
        "    print('days', report['days'])\n"
        "asyncio.run(main())\n"
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-",
        admin,
        stdin=PIPE,
        stdout=PIPE,
        env={**os.environ, "RECONCILE_PARALLEL": "2"},
    )
    out, _ = await process.communicate(script.encode())
    assert process.returncode == 0
    assert out.decode().splitlines()[-1] == f"days {len(await _days(admin))}"


async def test_a_process_that_fails_stops_the_reconcile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An error in a process is the reconcile's error, not a hang."""
    admin = await _user(get_settings().admin_email)
    await _seed(admin)
    monkeypatch.setattr(get_settings(), "reconcile_parallel", 2)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:////nowhere/x.db")
    with pytest.raises(ExceptionGroup) as failed:
        await _reconcile(admin)
    assert "rollup process stopped" in str(failed.value.exceptions[0])
