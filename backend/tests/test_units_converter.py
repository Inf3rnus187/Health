"""Conversions prepared once per unit give what the per-value rule gave."""

from __future__ import annotations

import math

import pytest
from app.services.apple_health.units import (
    _FACTORS,
    _MOLAR_MASS,
    PERCENT_0_100,
    convert,
    converter,
)


def _rule(value: float, src: str, dst: str | None) -> float:
    """The rule as it was written, value by value (the reference)."""
    if src == PERCENT_0_100:
        return value
    if dst == "%" and 0.0 < value <= 1.0:
        return value * 100.0
    src = _MOLAR_MASS.sub("", src)
    if not dst or not src or src == dst:
        return value
    if src == "degF" and dst == "°C":
        return (value - 32.0) * 5.0 / 9.0
    return value * _FACTORS.get((src, dst), 1.0)


PAIRS = [*_FACTORS, ("degF", "°C"), ("", "kg"), ("kg", None), ("%", "%"),
         ("", "%"), (PERCENT_0_100, "%"), ("mmol<180.1558800000541>/L", "g/L"),
         ("count/min", "count/min"), ("unknown", "kg")]  # fmt: skip
VALUES = [0.0, -0.0, 1.0, 0.97, 0.5, 1.0000001, 97.0, -3.2, 123456.789,
          1e-9, math.inf, 0.1 + 0.2]  # fmt: skip


@pytest.mark.parametrize(("src", "dst"), PAIRS)
def test_the_same_number_to_the_last_bit(src: str, dst: str | None) -> None:
    for value in VALUES:
        expected = _rule(value, src, dst)
        for got in (converter(src, dst)(value), convert(value, src, dst)):
            assert repr(got) == repr(expected), (src, dst, value)


def test_nan_stays_nan() -> None:
    assert math.isnan(converter("lb", "kg")(math.nan))
