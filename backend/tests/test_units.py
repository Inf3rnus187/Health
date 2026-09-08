"""Unit tests for pure logic: aggregation and value coercion."""

from __future__ import annotations

from datetime import date, time
from typing import Any

import pytest
from app.core.errors import InvalidInputError
from app.models.metric import MetricDefinition
from app.services import measurement_values as mv
from app.services.aggregation import rolling

_PTS = [
    (date(2026, 1, 1), 10.0),
    (date(2026, 1, 2), 20.0),
    (date(2026, 1, 3), 30.0),
]


def _metric(data_type: str, **kw: Any) -> MetricDefinition:
    return MetricDefinition(
        key="x.y",
        label="l",
        domain="x",
        data_type=data_type,
        source="manual",
        aggregation_hint="avg",
        **kw,
    )


def test_rolling_supports_every_aggregation() -> None:
    assert rolling(_PTS, 7, "avg")[-1][1] == 20.0
    assert rolling(_PTS, 7, "sum")[-1][1] == 60.0
    assert rolling(_PTS, 7, "min")[-1][1] == 10.0
    assert rolling(_PTS, 7, "max")[-1][1] == 30.0
    assert rolling(_PTS, 7, "last")[-1][1] == 30.0
    assert rolling(_PTS, 1, "avg")[-1][1] == 30.0


def test_columns_route_by_type() -> None:
    assert mv.columns_for(_metric("time"), "23:30") == {
        "value_time": time(23, 30)
    }
    assert mv.columns_for(_metric("text"), "hi") == {"value_text": "hi"}
    assert mv.columns_for(_metric("bool"), True) == {"value_bool": True}
    assert mv.columns_for(_metric("int"), 5) == {"value_num": 5.0}
    assert mv.columns_for(_metric("text"), {"a": 1})["value_text"]


def test_json_type_wraps_scalars() -> None:
    assert mv.columns_for(_metric("text"), "x") == {"value_text": "x"}


def test_enum_validation() -> None:
    metric = _metric("enum", enum_options=["a", "b"])
    mv.validate(metric, "a")
    with pytest.raises(InvalidInputError):
        mv.validate(metric, "c")


def test_bad_number_rejected() -> None:
    with pytest.raises(InvalidInputError):
        mv.columns_for(_metric("float"), "abc")


def test_bad_time_rejected() -> None:
    with pytest.raises(InvalidInputError):
        mv.columns_for(_metric("time"), "not-a-time")
