"""Stream an Apple Health ``export.xml`` into canonical samples.

The export is often hundreds of megabytes, so it is parsed with
``iterparse`` and the tree is cleared after every top-level element to
keep memory flat. Each yielded :class:`Sample` is already resolved to a
metric key and converted to that metric's canonical unit.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import NamedTuple
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import iterparse

from app.services.apple_health.spec import (
    CANON_UNIT,
    QUANTITY_MAP,
    SLEEP_MAP,
    SLEEP_TYPE,
    WORKOUT_MAP,
)
from app.services.apple_health.units import convert


class Sample(NamedTuple):
    """One value bound to a metric key and day, in canonical units."""

    metric_key: str
    day: date
    value: float


def parse(path: str) -> Iterator[Sample]:
    """Yield canonical samples from every Record and Workout element."""
    depth = 0
    root: Element | None = None
    for event, elem in iterparse(path, events=("start", "end")):
        if event == "start":
            depth += 1
            root = root or elem
            continue
        depth -= 1
        if depth == 1 and root is not None:
            yield from _emit(elem)
            root.clear()


def _emit(elem: Element) -> Iterator[Sample]:
    """Dispatch a top-level element to its sample builder."""
    if elem.tag == "Record":
        return _record(elem)
    if elem.tag == "Workout":
        return _workout(elem)
    return iter(())


def _record(elem: Element) -> Iterator[Sample]:
    """Build samples from a quantity or sleep-analysis record."""
    rtype = elem.get("type", "")
    if rtype in QUANTITY_MAP:
        return _quantity(elem, rtype)
    if rtype == SLEEP_TYPE:
        return _sleep(elem)
    return iter(())


def _quantity(elem: Element, rtype: str) -> Iterator[Sample]:
    """Emit one sample per target metric of a quantity record."""
    raw = _to_float(elem.get("value"))
    day = _day(elem.get("startDate"))
    if raw is None or day is None:
        return
    unit = elem.get("unit", "")
    for key in QUANTITY_MAP[rtype]:
        yield Sample(key, day, convert(raw, unit, CANON_UNIT.get(key)))


def _sleep(elem: Element) -> Iterator[Sample]:
    """Emit sleep-stage minutes bucketed by the wake-up day."""
    keys = SLEEP_MAP.get(elem.get("value", ""))
    minutes = _minutes(elem)
    day = _day(elem.get("endDate"))
    if not keys or minutes is None or day is None:
        return
    for key in keys:
        yield Sample(key, day, minutes)


def _workout(elem: Element) -> Iterator[Sample]:
    """Emit a session count plus its duration, energy and distance."""
    day = _day(elem.get("startDate"))
    if day is None:
        return
    yield Sample("workout.count", day, 1.0)
    for attr, key in WORKOUT_MAP:
        value = _to_float(elem.get(attr))
        if value is None:
            continue
        unit = elem.get(f"{attr}Unit", "")
        yield Sample(key, day, convert(value, unit, CANON_UNIT.get(key)))


def _minutes(elem: Element) -> float | None:
    """Return the record's span in minutes, or ``None`` if unparsable."""
    start = _stamp(elem.get("startDate"))
    end = _stamp(elem.get("endDate"))
    if start is None or end is None:
        return None
    return (end - start).total_seconds() / 60.0


def _to_float(raw: str | None) -> float | None:
    """Parse a numeric attribute, tolerating missing or bad values."""
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _day(raw: str | None) -> date | None:
    """Read the calendar day from an Apple timestamp attribute."""
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _stamp(raw: str | None) -> datetime | None:
    """Parse a full Apple timestamp (``YYYY-MM-DD HH:MM:SS ±ZZZZ``)."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return None
