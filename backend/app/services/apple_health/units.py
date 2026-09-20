"""Convert a HealthKit sample value to a metric's canonical unit.

HealthKit records carry their own unit (``mi``, ``lb``, ``mL`` …); the
metric registry stores one canonical unit per key. Unknown pairs pass
through unchanged so an unexpected unit never aborts an import.
"""

from __future__ import annotations

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
}


def convert(value: float, src: str, dst: str | None) -> float:
    """Return ``value`` expressed in the destination unit."""
    if dst == "%" and 0.0 < value <= 1.0:
        return value * 100.0
    if not dst or not src or src == dst:
        return value
    if src == "degF" and dst == "°C":
        return (value - 32.0) * 5.0 / 9.0
    return value * _FACTORS.get((src, dst), 1.0)
