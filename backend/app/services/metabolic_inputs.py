"""Load the dated history of every marker input, in the formulas' units.

Each input may come from several metric keys (e.g. a tape measure typed
in the web form or Apple Health's waist circumference); all their values
are merged into one dated series so the latest value and any past value
can be looked up the same way.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services import metabolic_catalog as cat

_METRES_MAX = 3.0  # a height below 3 is in metres
_MG_DL_MIN = 20.0  # TG / glucose above 20 are in mg/dL
_MMOL_MIN = 3.0  # glucose between 3 and 20 is in mmol/L
_IFCC_MIN = 20.0  # HbA1c above 20 is in mmol/mol (IFCC)


class Value(NamedTuple):
    """One dated value of an input."""

    value: float
    day: date


Series = dict[str, list[Value]]


async def load(session: AsyncSession, user_id: str) -> Series:
    """Every input's values, oldest first, one per day."""
    keys = {key: name for name, group in cat.SOURCES.items() for key in group}
    result = await session.execute(
        select(
            MetricDefinition.key, Measurement.value_num, Measurement.date_key
        )
        .join(MetricDefinition, Measurement.metric_id == MetricDefinition.id)
        .where(
            Measurement.user_id == user_id,
            MetricDefinition.key.in_(keys),
            Measurement.value_num.is_not(None),
        )
        .order_by(Measurement.date_key)
    )
    by_day: dict[str, dict[date, float]] = {}
    for key, num, day in result.all():
        by_day.setdefault(keys[key], {})[day] = _normalize(keys[key], num)
    return {
        name: [Value(v, d) for d, v in sorted(days.items())]
        for name, days in by_day.items()
    }


def latest(series: Series) -> dict[str, Value]:
    """Most recent value of each input."""
    return {name: values[-1] for name, values in series.items() if values}


def as_of(series: Series, name: str, day: date) -> Value | None:
    """Latest value of ``name`` on or before ``day``, if recent enough."""
    oldest = day - timedelta(days=cat.MAX_AGE.get(name, cat.DEFAULT_MAX_AGE))
    found = None
    for value in series.get(name, []):
        if value.day > day:
            break
        found = value
    if found is None:
        return None
    return found if name in cat.STATIC or found.day >= oldest else None


def _normalize(name: str, number: float) -> float:
    """Bring common alternative units back to the formulas' units."""
    x = float(number)
    if name == "height" and x < _METRES_MAX:
        x *= 100  # metres -> cm
    elif name in ("tg", "glucose") and x > _MG_DL_MIN:
        x /= 100  # mg/dL -> g/L
    elif name == "glucose" and x > _MMOL_MIN:
        x *= 0.18  # mmol/L -> g/L
    elif name == "hba1c" and x > _IFCC_MIN:
        x = 0.09148 * x + 2.152  # IFCC mmol/mol -> NGSP %
    return x
