"""Steps timed one by one: order, sums, total."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.core import timing


def _clock(times: list[float]) -> Iterator[float]:
    yield from times


def test_each_step_is_timed_in_order_and_added_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # start, a in/out, b in/out, a again in/out, report
    ticks = _clock([0.0, 0.0, 0.010, 0.010, 0.250, 0.250, 0.255, 0.300])
    monkeypatch.setattr(timing.time, "perf_counter", lambda: next(ticks))
    steps = timing.Steps()
    with steps.step("a"):
        pass
    with steps.step("b"):
        pass
    with steps.step("a"):
        pass
    assert steps.report() == {"a": 15, "b": 240, "total": 300}


def test_a_failing_step_is_timed_too(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = _clock([0.0, 0.0, 0.020, 0.030])
    monkeypatch.setattr(timing.time, "perf_counter", lambda: next(ticks))
    steps = timing.Steps()
    with pytest.raises(ValueError, match="bad"), steps.step("read"):
        raise ValueError("bad")
    assert steps.report() == {"read": 20, "total": 30}


def test_a_lap_counts_since_the_last_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # (started 1.0 given) step in/out, lap now, report
    ticks = _clock([1.100, 1.150, 1.400, 1.500])
    monkeypatch.setattr(timing.time, "perf_counter", lambda: next(ticks))
    steps = timing.Steps(started=1.0)
    steps.lap("before", at=1.100)
    with steps.step("work"):
        pass
    steps.lap("after")
    assert steps.report() == {
        "before": 100, "work": 50, "after": 250, "total": 500
    }  # fmt: skip


async def test_a_request_clock_starts_when_the_request_arrived(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from starlette.requests import Request

    ticks = _clock([2.030, 2.100])  # dependency called, then report
    monkeypatch.setattr(timing.time, "perf_counter", lambda: next(ticks))
    state = {"started": 2.0, "received": 2.020}
    request = Request({"type": "http", "state": state})
    steps = await timing.request_steps(request)
    assert steps.report() == {"receive": 20, "json": 10, "total": 100}
