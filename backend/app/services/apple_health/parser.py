"""Stream raw records and workouts from an Apple Health ``export.xml``.

The file (often hundreds of MB) is parsed incrementally with
``defusedxml.iterparse`` and the tree is cleared after every top-level
element, so memory stays flat regardless of size. Values are yielded raw;
the importer resolves metrics, units and timestamps.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import IO, NamedTuple
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import iterparse


class RawRecord(NamedTuple):
    """A single quantity or category record, unparsed."""

    hk_type: str
    unit: str | None
    value: str | None
    start: str | None
    end: str | None
    device: str | None


class RawWorkout(NamedTuple):
    """A workout element with its numeric attributes kept as strings."""

    activity_type: str
    start: str | None
    end: str | None
    attrs: dict[str, str]


Item = tuple[str, RawRecord | RawWorkout]


def parse_xml(source: IO[bytes]) -> Iterator[Item]:
    """Yield ``("record"|"workout", obj)`` for every top-level element."""
    depth = 0
    root: Element | None = None
    for event, elem in iterparse(source, events=("start", "end")):
        if event == "start":
            depth += 1
            root = root or elem
            continue
        depth -= 1
        if depth == 1 and root is not None:
            item = _emit(elem)
            if item is not None:
                yield item
            root.clear()


def _emit(elem: Element) -> Item | None:
    """Convert a Record or Workout element to a raw item."""
    if elem.tag == "Record":
        return ("record", _record(elem))
    if elem.tag == "Workout":
        return ("workout", _workout(elem))
    return None


def _record(elem: Element) -> RawRecord:
    """Read the attributes of a Record element."""
    return RawRecord(
        hk_type=elem.get("type", ""),
        unit=elem.get("unit"),
        value=elem.get("value"),
        start=elem.get("startDate"),
        end=elem.get("endDate"),
        device=elem.get("sourceName"),
    )


def _workout(elem: Element) -> RawWorkout:
    """Read a Workout element and its numeric attributes."""
    attrs = {
        name: value
        for name in _WORKOUT_KEYS
        if (value := elem.get(name)) is not None
    }
    return RawWorkout(
        activity_type=elem.get("workoutActivityType", "workout"),
        start=elem.get("startDate"),
        end=elem.get("endDate"),
        attrs=attrs,
    )


_WORKOUT_KEYS = (
    "duration",
    "durationUnit",
    "totalEnergyBurned",
    "totalEnergyBurnedUnit",
    "totalDistance",
    "totalDistanceUnit",
)
