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
