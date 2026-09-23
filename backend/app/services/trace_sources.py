"""Traces from documents and ticket exports (see :mod:`trace_import`).

- a receipt or an invoice (PDF, photo): one trace, the file its proof;
- an expense report (Lucca « Note de frais »): one trace per expense,
  known by its day, with its comment; the PDF itself is kept once,
  untouched, as a document (its seal stays verifiable);
- a ticket export (NinjaOne…): the chosen person's actions, one trace a
  day from the first to the last, each action listed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.services import (
    expense_report_read,
    receipt_read,
    ticket_read,
    trace_columns,
)
from app.services.table_read import Row
from app.services.trace_model import Trace, noon

_PDF = "application/pdf"
_MINUTE = timedelta(minutes=1)


def document(
    data: bytes, name: str, kind: str, tz: ZoneInfo
) -> tuple[list[Trace], list[dict[str, Any]], dict[str, Any]]:
    """A receipt, or an expense report: its traces and what was read."""
    text = expense_report_read.text_of(data) if data[:5] == b"%PDF-" else ""
    if expense_report_read.is_report(text):
        report = expense_report_read.read(data, text)
        about = f"{report.label} : {len(report.lines)} dépenses"
        return _report(report, (name, data), tz), [], {"document": about}
    receipt = receipt_read.read(data, name, tz)
    if receipt is None:
        return [], [{"line": 1, "reason": "aucune date lisible"}], {}
    trace = Trace(
        start=receipt.start.astimezone(UTC),
        end=None,
        time_known=receipt.time_known,
        kind=(receipt.kind or "frais") if kind == "auto" else kind,
        place="",
        vendor=receipt.vendor,
        amount=receipt.amount,
        currency="EUR",
        what=receipt.what,
        group=name,
        file=(name, receipt.media_type, data),
    )
    return [trace], [], {"document": "reçu / facture lu"}


def _report(
    report: expense_report_read.Report, file: tuple[str, bytes], tz: ZoneInfo
) -> list[Trace]:
    """One trace per expense, and the report kept as a document."""
    out = [_expense(line, report.label, tz) for line in report.lines]
    total = round(sum(t.amount or 0 for t in out), 2)
    first = min((line.day for line in report.lines), default=None)
    when = report.issued.replace(tzinfo=tz) if report.issued else None
    start = (
        when.astimezone(UTC)
        if when
        else (noon(first, tz) if first else datetime.now(UTC))
    )
    name, data = file
    kept = Trace(
        start=start,
        end=None,
        time_known=report.timed,
        kind="document",
        place="",
        vendor=report.label,
        amount=None,
        currency="EUR",
        what=f"{len(out)} dépenses, {total:.2f} € — PDF d'origine intact",
        group=name,
        file=(name, _PDF, data),
    )
    return [kept, *out]


def _expense(line: expense_report_read.Line, label: str, tz: ZoneInfo) -> Trace:
    """One expense line: its day, kind, supplier, amount and comment."""
    parts = [line.comment, f"payé {line.paid}" if line.paid else ""]
    parts.append(f"{label}, dépense #{line.number}")
    return Trace(
        start=noon(line.day, tz),
        end=None,
        time_known=False,
        kind=trace_columns.kind_of(f"{line.nature} {line.vendor}") or "frais",
        place="",
        vendor=line.vendor[:200],
        amount=line.amount,
        currency="EUR",
        what=" · ".join(p for p in parts if p)[:500],
        group=f"{label}#{line.number}",
    )


def tickets(
    rows: list[Row], person: str, tz: ZoneInfo
) -> tuple[list[Trace], dict[str, Any]] | None:
    """A ticket export's traces for ``person`` (None: not tickets)."""
    cols = ticket_read.columns(rows)
    if not cols:
        return None
    found = ticket_read.people(rows, cols)
    who = person.strip() or (found[0][0] if found else "")
    days = ticket_read.days(rows, cols, who, tz)
    about = {
        "tickets": f"actions de {who}" if who else "aucun auteur",
        "person": who,
        "people": [{"name": n, "actions": c} for n, c in found[:15]],
    }
    return [_activity(day, who) for day in days], about


def _activity(day: ticket_read.Day, who: str) -> Trace:
    """A day of actions: first → last, each one listed."""
    count = len(day.actions)
    return Trace(
        start=day.first,
        end=day.last if day.last - day.first >= _MINUTE else None,
        time_known=True,
        kind="activite",
        place="",
        vendor=f"Tickets — {count} action{'s' if count > 1 else ''}",
        amount=None,
        currency="EUR",
        what=(f"{who} : " + " ; ".join(day.actions))[:4000],
        group=f"tickets-{day.day}",
        actions=count,
    )
