"""Parse a "SimpleHealthExportCSV" export into raw records.

The RoutineHub *SimpleHealthExportCSV* shortcut writes one CSV per
HealthKit type, keyed by a ``type,sourceName,...,unit,value`` header. Each
data row is yielded as the same :class:`RawRecord` the XML importer emits,
so CSV rows flow through identical raw storage and daily roll-ups. Column
order varies between files (metadata columns differ), so rows are read by
header name, not position.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from typing import TextIO

from app.services.apple_health.parser import Item, RawRecord

_BOM = b"\xef\xbb\xbf"


def is_health_csv(head: bytes) -> bool:
    """True if the first bytes look like a SimpleHealthExportCSV header."""
    body = head[len(_BOM) :] if head.startswith(_BOM) else head
    return body.lstrip().lower().startswith(b"type,")


def iter_csv_records(stream: TextIO) -> Iterator[Item]:
    """Yield ``("record", RawRecord)`` for each usable data row."""
    reader = csv.DictReader(stream)
    if reader.fieldnames is None or "type" not in reader.fieldnames:
        return
    for row in reader:
        record = _row_record(row)
        if record is not None:
            yield ("record", record)


def _row_record(row: dict[str, str | None]) -> RawRecord | None:
    """Build a RawRecord from one CSV row, or ``None`` if unusable."""
    hk_type = (row.get("type") or "").strip()
    if not hk_type.startswith("HK"):
        return None
    return RawRecord(
        hk_type=hk_type,
        unit=_clean(row.get("unit")),
        value=_clean(row.get("value")),
        start=_clean(row.get("startDate")),
        end=_clean(row.get("endDate")),
        device=_clean(row.get("sourceName")),
    )


def _clean(value: str | None) -> str | None:
    """Trim a CSV cell, mapping empty to ``None``."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None
