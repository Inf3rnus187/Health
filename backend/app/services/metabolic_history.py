"""Past values of a marker, recomputed at every lab / FibroScan date.

Lab reports carry previous results ("antériorités"), so each marker can
be followed over time: at every date where one of its event inputs was
measured, it is recomputed with the values known on that day (each
looked up within a staleness limit, e.g. weight within 30 days).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services import metabolic_catalog as cat
from app.services import metabolic_inputs as inputs
from app.services.metabolic_inputs import Series

_MAX_POINTS = 12


def history(spec: cat.Spec, series: Series) -> list[dict[str, Any]]:
    """The marker at each of its event dates, oldest first (last 12)."""
    days = sorted(
        {
            value.day
            for name in spec.needs
            if name in cat.EVENTS
            for value in series.get(name, [])
        }
    )
    points = [_at(spec, series, day) for day in days]
    return [p for p in points if p is not None][-_MAX_POINTS:]


def _at(spec: cat.Spec, series: Series, day: date) -> dict[str, Any] | None:
    """The marker computed with the inputs known on ``day``."""
    found = {name: inputs.as_of(series, name, day) for name in spec.needs}
    values = {name: v.value for name, v in found.items() if v is not None}
    if len(values) < len(spec.needs):
        return None
    try:
        value = spec.compute(values)
    except (ValueError, ZeroDivisionError):
        return None
    band = cat.band_for(spec, values, value)
    return {
        "date": day.isoformat(),
        "value": round(value, spec.digits),
        "level": band.level,
    }
