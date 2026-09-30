"""Convert a HealthKit sample value to a metric's canonical unit.

HealthKit records carry their own unit (``mi``, ``lb``, ``mL`` …); the
metric registry stores one canonical unit per key. Unknown pairs pass
through unchanged so an unexpected unit never aborts an import.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache

# HealthKit spells glucose molarity with its molar mass: mmol<180.15…>/L.
_MOLAR_MASS = re.compile(r"<[^>]*>")

#: (source unit, destination unit) → multiplier.
_FACTORS: dict[tuple[str, str], float] = {
    ("mi", "km"): 1.609344,
    ("m", "km"): 0.001,
    ("lb", "kg"): 0.45359237,
    ("g", "kg"): 0.001,
    ("mL", "L"): 0.001,
    ("fl_oz_us", "L"): 0.0295735,
    ("kJ", "kcal"): 0.239006,
    ("in", "cm"): 2.54,
    ("ft", "cm"): 30.48,
    ("m", "cm"): 100.0,
    ("hr", "min"): 60.0,
    ("mg/dL", "g/L"): 0.01,
    ("mmol/L", "g/L"): 0.18,  # glucose (180.16 g/mol)
    ("m/s", "km/hr"): 3.6,
    ("mi/hr", "km/hr"): 1.609344,
    ("ft/s", "m/s"): 0.3048,
    ("yd", "m"): 0.9144,
    ("ft", "m"): 0.3048,
    ("in", "m"): 0.0254,
    ("count/s", "count/min"): 60.0,
    ("Cal", "kcal"): 1.0,
    ("S", "mcS"): 1_000_000.0,
    ("fl_oz_us", "mL"): 29.5735,
    ("L", "mL"): 1000.0,
    ("s", "min"): 1 / 60,
}

#: Percentages already on a 0-100 scale (Health Auto Export); the Apple
#: export writes them as fractions (0.97), which are scaled to %.
PERCENT_0_100 = "pct"


def convert(value: float, src: str, dst: str | None) -> float:
    """Return ``value`` expressed in the destination unit."""
    return converter(src, dst)(value)


@lru_cache(maxsize=512)
def converter(src: str, dst: str | None) -> Callable[[float], float]:
    """The conversion from ``src`` to ``dst``, prepared once per pair.

    A fraction (0.97) becomes a percentage whatever its unit; a 0-100
    percentage stays; the unit's molar mass is ignored; °F becomes °C;
    else the pair's factor (none: unchanged). A rebuild of millions of
    samples prepares it once per unit, not once per sample.
    """
    if src == PERCENT_0_100:
        return _same
    rest = _plain(_MOLAR_MASS.sub("", src), dst)
    if dst == "%":
        return lambda v: v * 100.0 if 0.0 < v <= 1.0 else rest(v)
    return rest


def _plain(src: str, dst: str | None) -> Callable[[float], float]:
    """Without the fraction rule: same, °F → °C, or a factor."""
    if not dst or not src or src == dst:
        return _same
    if src == "degF" and dst == "°C":
        return _fahrenheit
    factor = _FACTORS.get((src, dst), 1.0)
    return lambda v: v * factor


def _same(value: float) -> float:
    """Unchanged."""
    return value


def _fahrenheit(value: float) -> float:
    """°F → °C."""
    return (value - 32.0) * 5.0 / 9.0
