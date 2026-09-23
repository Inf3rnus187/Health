"""Import past clock-in / clock-out logs (txt, csv, json) as sessions.

Lines are read by :mod:`work_parse`. A CSV header (``Date;Embauche;
Débauche``) names the columns of the rows under it. A JSON file is read
record by record (``{"date": …, "embauche": …, "debauche": …}``, lists of
such records, or lists of lines). Times without an offset are the
user's local times. Nothing is written in a dry run; a real run adds or
updates sessions (same start: updated), so importing twice is harmless.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError
from app.services import work, work_parse
from app.services.daily_rollup import user_zone
from app.services.work_parse import Event, Span

#: At most this many unreadable lines are listed back.
MAX_SKIPPED = 50
_DELIMITER = re.compile(r"[;,\t|]")


def lines_of(data: bytes, filename: str) -> list[str]:
    """The text lines of a file (a JSON file: one line per record)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    if filename.lower().endswith(".json") or text.lstrip()[:1] in "[{":
        try:
            return _json_lines(json.loads(text))
        except ValueError:
            pass
    return text.splitlines()


def read(
    data: bytes, filename: str
) -> tuple[list[Event], list[dict[str, Any]]]:
    """Every clock event of a file, and the lines that were not understood."""
    events: list[Event] = []
    skipped: list[dict[str, Any]] = []
    header: list[str] | None = None
    for number, raw in enumerate(lines_of(data, filename), start=1):
        if _is_header(raw):
            header = _DELIMITER.split(raw)
            continue
        line = _with_header(raw, header) if header else raw
        found, reason = work_parse.read_line(line, number)
        events.extend(found)
        if reason:
            skipped.append(
                {"line": number, "text": raw[:120], "reason": reason}
            )
    return events, skipped


async def import_file(
    session: AsyncSession,
    user_id: str,
    data: bytes,
    filename: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Read a log and (unless ``dry_run``) store its sessions."""
    tz = await user_zone(session, user_id)
    events, unread = read(data, filename)
    aware = [_aware(e, tz) for e in events]
    spans, notes = work_parse.pair(aware, tz)
    stored, refused = 0, list[dict[str, Any]]()
    if not dry_run:
        stored, refused = await store(session, user_id, spans)
    return summary(spans, unread + refused, notes, tz, stored, dry_run)


async def store(
    session: AsyncSession, user_id: str, spans: list[Span]
) -> tuple[int, list[dict[str, Any]]]:
    """Add the sessions; the refused ones (overlaps) are listed back."""
    stored, refused = 0, list[dict[str, Any]]()
    for start, end in spans:
        fields = {"start_at": start, "end_at": end, "note": ""}
        try:
            await work.add(session, user_id, fields, "import")
            stored += 1
        except InvalidInputError as exc:
            at = (start or end or datetime.now(UTC)).isoformat()
            refused.append({"at": at, "reason": str(exc)})
    return stored, refused


def summary(
    spans: list[Span],
    skipped: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    tz: ZoneInfo,
    stored: int,
    dry_run: bool,
) -> dict[str, Any]:
    """What was found (and stored): counts, hours, days, a preview."""
    days = sorted({_local(s or e, tz).date() for s, e in spans if s or e})
    whole = [(s, e) for s, e in spans if s and e]
    return {
        "dry_run": dry_run,
        "sessions": len(spans),
        "complete": len(whole),
        "missing_start": sum(1 for s, _ in spans if s is None),
        "missing_end": sum(1 for _, e in spans if e is None),
        "stored": stored,
        "days": len(days),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "total_hours": round(
            sum((e - s).total_seconds() for s, e in whole) / 3600, 2
        ),
        "preview": [_preview(span, tz) for span in spans[:10]],
        "notes": notes[:MAX_SKIPPED],
        "skipped_count": len(skipped),
        "skipped": skipped[:MAX_SKIPPED],
    }


def _preview(span: Span, tz: ZoneInfo) -> dict[str, Any]:
    """One session for the preview (a missing half shows "?")."""
    start, end = span
    anchor = _local(start or end, tz)
    return {
        "day": anchor.date(),
        "start": f"{_local(start, tz):%H:%M}" if start else "?",
        "end": f"{_local(end, tz):%H:%M}" if end else "?",
    }


def _local(at: datetime | None, tz: ZoneInfo) -> datetime:
    """A stored instant in local time."""
    return (at or datetime.now(UTC)).astimezone(tz)


def _aware(event: Event, tz: ZoneInfo) -> Event:
    """An event with an aware UTC time (no offset: the user's local)."""
    at = event.at if event.at.tzinfo else event.at.replace(tzinfo=tz)
    return event._replace(at=at.astimezone(UTC))


def _is_header(line: str) -> bool:
    """A column-title line: delimited, no digit, names a column."""
    return (
        not any(ch.isdigit() for ch in line)
        and len(_DELIMITER.split(line)) > 1
        and bool(line.strip())
    )


def _with_header(line: str, header: list[str]) -> str:
    """Put each column's title before its cell (``Embauche 08:12``)."""
    cells = _DELIMITER.split(line)
    if len(cells) != len(header):
        return line
    pairs = zip(header, cells, strict=True)
    return " ; ".join(f"{title} {cell}" for title, cell in pairs)


def _json_lines(value: Any) -> list[str]:
    """One text line per JSON record (keys kept: they name the times)."""
    if isinstance(value, list):
        return [line for item in value for line in _json_lines(item)]
    if isinstance(value, dict):
        nested = [v for v in value.values() if isinstance(v, list | dict)]
        if nested and len(nested) == len(value):
            return [line for item in nested for line in _json_lines(item)]
        return [
            " ; ".join(
                f"{key} {val}"
                for key, val in value.items()
                if not isinstance(val, list | dict)
            )
        ]
    return [str(value)]
