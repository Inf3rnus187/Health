"""Import traces from app exports: rides, deliveries, transport, parking.

One file, one kind (taxi / VTC, delivered meals, transport pass,
parking, hotel, expense report…). Columns are found by their titles
(:mod:`trace_columns`); cancelled rows are skipped; the rows of one
delivery order are merged; a trace already stored (same kind, same
minute, same amount) is not added twice. Deliveries can also be logged
as meals, with their price, for the AI to read.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.models.work import Evidence
from app.services import evidence, table_read, trace_columns, traces, work_parse
from app.services.daily_rollup import user_zone
from app.services.trace_columns import Columns

MAX_LISTED = 50
#: The time given to a trace known only by its date.
_NOON = time(12, 0)


class Trace(NamedTuple):
    """One trace read from a row (times in UTC)."""

    start: datetime
    end: datetime | None
    place: str
    amount: float | None
    currency: str
    what: str
    group: str


async def import_traces(
    session: AsyncSession,
    user_id: str,
    files: list[tuple[str, str, bytes]],
    *,
    dry_run: bool,
    meals: bool,
) -> tuple[dict[str, Any], list[Meal]]:
    """Import ``(file name, kind, content)`` files; meals to read after."""
    tz = await user_zone(session, user_id)
    report: dict[str, Any] = {"dry_run": dry_run, "files": []}
    logged: list[Meal] = []
    for name, kind, data in files:
        found, skipped, columns = read(data, name, kind, tz)
        new = [t for t in found if not await _stored(session, user_id, kind, t)]
        if not dry_run:
            logged += await _store(session, user_id, kind, new, meals)
        report["files"].append(
            _summary(name, kind, (found, new, skipped), columns, tz, dry_run)
        )
    return report, logged


def read(
    data: bytes, name: str, kind: str, tz: ZoneInfo
) -> tuple[list[Trace], list[dict[str, Any]], Columns]:
    """The traces of a file, the rows left out and the columns found."""
    rows = table_read.rows_of(data, name)
    columns = trace_columns.find(rows)
    found: list[Trace] = []
    skipped: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=2):
        status = work_parse.fold(row.get(columns.status or "", ""))
        start = _when(row, columns, tz)
        if trace_columns.CANCELLED.search(status):
            skipped.append({"line": number, "reason": "annulé"})
        elif start is None:
            skipped.append({"line": number, "reason": "pas de date ni d'heure"})
        else:
            found.append(_trace(row, columns, start, tz))
    return (
        (_orders(found) if kind in traces.MEAL_KINDS else found),
        skipped,
        columns,
    )


def _trace(
    row: table_read.Row, c: Columns, start: datetime, tz: ZoneInfo
) -> Trace:
    """A row as a trace."""
    end = _stamp(row.get(c.end or "", ""), tz) if c.end else None
    group = (
        row.get(c.order or "", "")
        or f"{start.isoformat()}|{row.get(c.place or '', '')}"
    )
    return Trace(
        start=start,
        end=end if end and end > start else None,
        place=row.get(c.place or "", "")[:300],
        amount=trace_columns.amount(row.get(c.amount or "", "")),
        currency=(row.get(c.currency or "", "") or "EUR")[:3].upper(),
        what=row.get(c.what or "", "")[:500],
        group=group,
    )  # fmt: skip


def _when(row: table_read.Row, c: Columns, tz: ZoneInfo) -> datetime | None:
    """The row's start: a date-time column, else a date and a time."""
    if c.start:
        return _stamp(row.get(c.start, ""), tz)
    if c.date:
        return _stamp(f"{row.get(c.date, '')} {row.get(c.time or '', '')}", tz)
    return None


def _stamp(text: str, tz: ZoneInfo) -> datetime | None:
    """The first date-time of a text, in UTC (no offset: local time)."""
    found = work_parse.stamps(text)
    if found:
        at = found[0] if found[0].tzinfo else found[0].replace(tzinfo=tz)
        return at.astimezone(UTC)
    day = work_parse.day_of(text)  # a date alone: an expense, a hotel
    if day is None:
        return None
    return datetime.combine(day, _NOON, tzinfo=tz).astimezone(UTC)


def _orders(found: list[Trace]) -> list[Trace]:
    """The rows of one order merged (items listed, price counted once)."""
    groups: dict[str, list[Trace]] = {}
    for trace in found:
        groups.setdefault(trace.group, []).append(trace)
    merged = []
    for rows in groups.values():
        prices = [t.amount for t in rows if t.amount is not None]
        once = len(set(prices)) == 1  # the order total repeated per item
        items = ", ".join(dict.fromkeys(t.what for t in rows if t.what))
        merged.append(
            rows[0]._replace(
                amount=(prices[0] if once else round(sum(prices), 2))
                if prices
                else None,
                what=items[:500],
            )
        )
    return merged


async def _stored(
    session: AsyncSession, user_id: str, kind: str, trace: Trace
) -> bool:
    """Whether the same trace is already stored (same kind, minute, price)."""
    rows = await session.execute(
        select(Evidence.amount).where(
            Evidence.user_id == user_id,
            Evidence.kind == kind,
            Evidence.occurred_at.between(
                trace.start - timedelta(minutes=1),
                trace.start + timedelta(minutes=1),
            ),
        )
    )
    return any(a == trace.amount for a in rows.scalars())


async def _store(
    session: AsyncSession,
    user_id: str,
    kind: str,
    new: list[Trace],
    meals: bool,
) -> list[Meal]:
    """Store the traces; the meals logged from deliveries are returned."""
    logged = []
    for t in new:
        fields = {
            "occurred_at": t.start, "ended_at": t.end, "kind": kind,
            "title": t.place or evidence.KINDS.get(kind, kind),
            "description": t.what, "place": t.place, "amount": t.amount,
            "currency": t.currency,
        }  # fmt: skip
        row = await evidence.create(session, user_id, fields, None)
        if meals and kind in traces.MEAL_KINDS:
            logged.append(await traces.add_meal(session, row, t.what))
    return logged


def _summary(
    name: str,
    kind: str,
    parts: tuple[list[Trace], list[Trace], list[dict[str, Any]]],
    columns: Columns,
    tz: ZoneInfo,
    dry_run: bool,
) -> dict[str, Any]:
    """What one file held."""
    found, new, skipped = parts
    days: list[date] = sorted({t.start.astimezone(tz).date() for t in found})
    return {
        "name": name,
        "kind": kind,
        "label": evidence.KINDS.get(kind, kind),
        "traces": len(found),
        "new": len(new),
        "duplicates": len(found) - len(new),
        "stored": 0 if dry_run else len(new),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "total": round(sum(t.amount or 0 for t in new), 2),
        "columns": {k: v for k, v in columns._asdict().items() if v},
        "preview": [_preview(t, tz) for t in found[:8]],
        "skipped_count": len(skipped),
        "skipped": skipped[:MAX_LISTED],
    }


def _preview(trace: Trace, tz: ZoneInfo) -> dict[str, Any]:
    """One trace for the preview."""
    local = trace.start.astimezone(tz)
    return {
        "day": local.date(),
        "time": f"{local:%H:%M}",
        "end": f"{trace.end.astimezone(tz):%H:%M}" if trace.end else None,
        "place": trace.place,
        "amount": trace.amount,
        "what": trace.what[:120],
    }
