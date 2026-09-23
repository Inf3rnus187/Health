"""Headline metrics for the home page's health-hub recap.

Each tile carries the latest value, the time of the last raw reading, and
lightweight evolution stats (day-over-day delta, 7-day average, and a short
daily sparkline) so the home page reads like a dashboard, not a list.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.services import metric_overview

#: The metrics shown as tiles, in order (missing ones are skipped).
HEADLINE_KEYS = (
    "body.weight",
    "activity.steps",
    "activity.distance",
    "rest.hr",
    "heart.rate",
    "heart.hrv",
    "sleep.asleep",
    "body.spo2",
    "body.resp_rate",
    "activity.active_energy",
    "activity.exercise_min",
    "habit.cigarettes",
    "habit.coffee",
    "elimination.urination",
    "work.hours",
)

#: Units not worth printing next to a number ("5", not "5 count").
_BARE_UNITS = {"count"}

#: The stored bottle counter and the litres it represents (1 bottle = 1.5 L).
_WATER_KEY = "water.bottles_1_5"
_LITERS_PER_BOTTLE = 1.5


class Tile(NamedTuple):
    """One headline metric's latest value plus evolution stats."""

    key: str
    label: str
    unit: str | None
    value: float
    date_key: date
    at: datetime | None
    delta: float | None
    avg7: float | None
    spark: list[float]


async def headline(session: AsyncSession, user_id: str) -> list[Tile]:
    """Return the latest value + stats of each available headline metric."""
    tiles: list[Tile] = []
    for key in HEADLINE_KEYS:
        tile = await _tile(session, user_id, key)
        if tile is not None:
            tiles.append(tile)
    water = await _water_tile(session, user_id)
    if water is not None:
        tiles.append(water)
    return tiles


async def _water_tile(session: AsyncSession, user_id: str) -> Tile | None:
    """Litres d'eau (1.5 L per finished bottle) from the stored counter."""
    bottles = await _tile(session, user_id, _WATER_KEY)
    if bottles is None:
        return None
    return Tile(
        key="hydration.liters",
        label="Eau",
        unit="L",
        value=round(bottles.value * _LITERS_PER_BOTTLE, 2),
        date_key=bottles.date_key,
        at=None,
        delta=_liters(bottles.delta),
        avg7=_liters(bottles.avg7),
        spark=[round(v * _LITERS_PER_BOTTLE, 2) for v in bottles.spark],
    )


def _liters(bottles: float | None) -> float | None:
    """Bottles → litres (None stays None)."""
    return None if bottles is None else round(bottles * _LITERS_PER_BOTTLE, 2)


async def _tile(session: AsyncSession, user_id: str, key: str) -> Tile | None:
    """A tile built from the metric overview (same numbers everywhere)."""
    try:
        view = await metric_overview.overview(session, user_id, key, days=30)
    except NotFoundError:
        return None
    if view["latest"] is None:
        return None
    series = [point["value"] for point in view["series"]]
    # A value known only by its day shows no (made-up) time.
    at = view["latest"]["at"] if view["latest"]["timed"] else None
    return Tile(
        key=key,
        label=view["label"],
        unit=None if view["unit"] in _BARE_UNITS else view["unit"],
        value=view["latest"]["value"],
        date_key=date.fromisoformat(view["day"]["date"]),
        at=datetime.fromisoformat(at) if at else None,
        delta=_delta(series),
        avg7=view["avg7"],
        spark=_spark(series),
    )


_MIN_POINTS = 2


def _delta(series: list[float]) -> float | None:
    """Change between the two most recent daily values."""
    if len(series) < _MIN_POINTS:
        return None
    return round(series[-1] - series[-2], 2)


def _spark(series: list[float]) -> list[float]:
    """The last 14 daily values, for a sparkline."""
    return [round(value, 2) for value in series[-14:]]
