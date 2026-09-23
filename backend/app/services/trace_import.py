"""Import traces from app exports and receipts (rides, meals, parking…).

A file is either a table (CSV, Excel, JSON: Uber, Uber Eats, Navigo,
parking, expense reports, bank statements) or a receipt / invoice (PDF,
photo: :mod:`receipt_read`, the file kept as the proof). Uber's own
exports are read by their exact columns (:mod:`uber_read`); other
tables' columns are found by their titles (:mod:`trace_columns`); a
column naming each line's kind (taxi, parking, dîner…) wins over the
file's kind; a "du … au …" text gives a start and an end; cancelled
rows are skipped; one order's rows are merged. The same trace met
twice — an expense line and its receipt: same kind, same day, same
amount, times equal or one unknown — is kept once, the receipt adding
its time and its file.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services import (
    chat_read,
    chat_traces,
    receipt_read,
    table_read,
    trace_columns,
    trace_sources,
    uber_read,
    work_parse,
)
from app.services.trace_columns import Columns
from app.services.trace_model import Trace, noon
from app.services.traces import MEAL_KINDS

_SPAN = re.compile(r"\s(?:au|a|to|->|→|jusqu'au)\s", re.IGNORECASE)


def read(
    data: bytes, name: str, kind: str, tz: ZoneInfo, person: str = ""
) -> tuple[list[Trace], list[dict[str, Any]], dict[str, Any]]:
    """The traces of a file, the rows left out and what was read.

    A ticket export or a WhatsApp chat gives the ``person``'s activity
    (default: the most active author, or « Moi » in a chat; the others
    listed to choose from).
    """
    if receipt_read.is_receipt(data, name):
        return trace_sources.document(data, name, kind, tz)
    if chat_read.is_chat(data, name):
        found, about = chat_traces.traces(data, name, person, tz)
        return found, [], about
    rows = table_read.rows_of(data, name)
    if not rows:
        return [], [{"line": 1, "reason": "fichier illisible ou vide"}], {}
    tickets = trace_sources.tickets(rows, person, tz)
    if tickets is not None:
        return tickets[0], [], tickets[1]
    uber = uber_read.read(rows, tz)
    if uber is not None:
        return uber
    columns = trace_columns.find(rows)
    found, skipped = _table(rows, columns, kind, tz)
    return _orders(found), skipped, _about(columns)


def _about(columns: Columns) -> dict[str, Any]:
    """The columns found, for the preview."""
    found = {k: v for k, v in columns._asdict().items() if v}
    return {**found, "extras": list(found.get("extras", ()))}


def _table(
    rows: list[table_read.Row], columns: Columns, kind: str, tz: ZoneInfo
) -> tuple[list[Trace], list[dict[str, Any]]]:
    """The traces of a table's rows and the rows left out."""
    found: list[Trace] = []
    skipped: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=2):
        status = work_parse.fold(row.get(columns.status or "", ""))
        when = _when(row, columns, tz)
        if trace_columns.CANCELLED.search(status):
            skipped.append({"line": number, "reason": "annulé"})
        elif when is None:
            skipped.append({"line": number, "reason": "pas de date"})
        else:
            found.append(_trace(row, columns, when, kind, tz))
    return found, skipped


def _trace(
    row: table_read.Row,
    c: Columns,
    when: tuple[datetime, bool],
    kind: str,
    tz: ZoneInfo,
) -> Trace:
    """A row as a trace."""

    def cell(key: str | None) -> str:
        return row.get(key or "", "")

    text = " · ".join(v for v in (cell(c.what), *map(cell, c.extras)) if v)
    start, known = when
    span = _span(" ".join((cell(c.place), text)), tz) if not known else None
    end = _stamp(cell(c.end), tz) if c.end else None
    row_kind = trace_columns.kind_of(cell(c.kind)) if c.kind else None
    return Trace(
        start=span[0] if span else start,
        end=span[1] if span else (end[0] if end and end[0] > start else None),
        time_known=bool(span) or known,
        kind=row_kind or (kind if kind != "auto" else "frais"),
        place=cell(c.place)[:300],
        vendor=cell(c.vendor)[:200],
        amount=trace_columns.amount(cell(c.amount)),
        currency=(cell(c.currency) or "EUR")[:3].upper(),
        what=text[:500],
        group=cell(c.order) or f"{start:%Y%m%d%H%M}{cell(c.vendor)}",
    )


def _when(
    row: table_read.Row, c: Columns, tz: ZoneInfo
) -> tuple[datetime, bool] | None:
    """The row's start: a date-time column, else a date and a time."""
    if c.start:
        return _stamp(row.get(c.start, ""), tz)
    if c.date:
        return _stamp(f"{row.get(c.date, '')} {row.get(c.time or '', '')}", tz)
    return None


def _stamp(text: str, tz: ZoneInfo) -> tuple[datetime, bool] | None:
    """The first date-time of a text in UTC, and whether its time is known."""
    found = work_parse.stamps(text)
    if found:
        at = found[0] if found[0].tzinfo else found[0].replace(tzinfo=tz)
        return at.astimezone(UTC), True
    day = work_parse.day_of(text)  # a date alone: an expense, a hotel
    if day is None:
        return None
    return noon(day, tz), False


def _span(text: str, tz: ZoneInfo) -> tuple[datetime, datetime] | None:
    """A "du 2/04/26 10h05 au 05/04/2026 23h32" text: start and end."""
    parts = _SPAN.split(text, maxsplit=1)
    if len(parts) != 2:  # noqa: PLR2004
        return None
    first, last = (work_parse.stamps(part) for part in parts)
    if not first or not last:
        return None
    start, end = (
        (s if s.tzinfo else s.replace(tzinfo=tz)).astimezone(UTC)
        for s in (first[0], last[0])
    )
    return (start, end) if end > start else None


def _orders(found: list[Trace]) -> list[Trace]:
    """The rows of one meal order merged (items listed, price once)."""
    groups: dict[str, list[Trace]] = {}
    for trace in found:
        key = trace.group if trace.kind in MEAL_KINDS else str(id(trace))
        groups.setdefault(key, []).append(trace)
    merged = []
    for rows in groups.values():
        prices = [t.amount for t in rows if t.amount is not None]
        once = len(set(prices)) == 1  # the order total repeated per item
        items = ", ".join(dict.fromkeys(t.what for t in rows if t.what))
        total = (
            (prices[0] if once else round(sum(prices), 2)) if prices else None
        )
        merged.append(rows[0]._replace(amount=total, what=items[:500]))
    return merged
