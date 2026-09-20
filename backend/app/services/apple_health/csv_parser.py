"""Parse a "SimpleHealthExportCSV" export into raw records.

The RoutineHub *SimpleHealthExportCSV* shortcut writes one CSV per
HealthKit type, keyed by a ``type,sourceName,...,unit,value`` header. Files
may start with an Excel ``sep=,`` preamble line and/or a UTF-8 BOM, and use
CRLF endings. Each data row is yielded as the same :class:`RawRecord` the
XML importer emits, so CSV rows flow through identical raw storage and
daily roll-ups. Column order varies between files (metadata columns
differ), so rows are read by header name, not position.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from typing import TextIO

from app.services.apple_health.parser import Item, RawRecord, RawWorkout

_BOM = b"\xef\xbb\xbf"
_WORKOUT_COLS = (
    "duration",
    "durationUnit",
    "totalEnergyBurned",
    "totalDistance",
)


def is_health_csv(head: bytes) -> bool:
    """True if the first bytes look like a SimpleHealthExportCSV header."""
    body = head[len(_BOM) :] if head.startswith(_BOM) else head
    text = body.lstrip().lower()
    if text.startswith(b"sep="):
        text = text.partition(b"\n")[2].lstrip()
    return text.startswith(b"type,")


def iter_csv_records(stream: TextIO) -> Iterator[Item]:
    """Yield ``("record"|"workout", …)`` for each usable data row."""
    reader = csv.DictReader(_rows(stream))
    if reader.fieldnames is None or "type" not in reader.fieldnames:
        return
    for row in reader:
        item = _row_item(row)
        if item is not None:
            yield item


def _rows(stream: TextIO) -> Iterator[str]:
    """Lines of a CSV, dropping a leading Excel ``sep=`` preamble line."""
    first = stream.readline()
    if not first:
        return
    if not first.lstrip().lower().startswith("sep="):
        yield first
    yield from stream


def _row_item(row: dict[str, str | None]) -> Item | None:
    """Turn one CSV row into a record or workout item."""
    hk_type = (row.get("type") or "").strip()
    if hk_type.startswith("HKWorkoutActivityType"):
        return ("workout", _row_workout(row, hk_type))
    if hk_type.startswith("HK"):
        return ("record", _row_record(row, hk_type))
    return None


def _row_record(row: dict[str, str | None], hk_type: str) -> RawRecord:
    """Build a RawRecord from one sample row."""
    return RawRecord(
        hk_type=hk_type,
        unit=_clean(row.get("unit")),
        value=_clean(row.get("value")),
        start=_clean(row.get("startDate")),
        end=_clean(row.get("endDate")),
        device=_clean(row.get("sourceName")),
    )


def _row_workout(row: dict[str, str | None], hk_type: str) -> RawWorkout:
    """Build a RawWorkout from one workout row."""
    attrs = {
        col: value
        for col in _WORKOUT_COLS
        if (value := _clean(row.get(col))) is not None
    }
    return RawWorkout(
        activity_type=hk_type,
        start=_clean(row.get("startDate")),
        end=_clean(row.get("endDate")),
        attrs=attrs,
    )


def _clean(value: str | None) -> str | None:
    """Trim a CSV cell, mapping empty to ``None``."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None
