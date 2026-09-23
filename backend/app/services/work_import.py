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

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError
from app.services import work, work_parse
from app.services.daily_rollup import user_zone
from app.services.work_parse import Event

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
    aware = [
        e._replace(
            at=(e.at if e.at.tzinfo else e.at.replace(tzinfo=tz)).astimezone(
                UTC
            )
        )
        for e in events
    ]
    sessions, unpaired = work_parse.pair(aware)
    skipped = unread + unpaired
    stored = 0
    if not dry_run:
        stored, refused = await _store(session, user_id, sessions)
        skipped += refused
    return _report(sessions, skipped, tz, dry_run, stored)


async def _store(
    session: AsyncSession,
    user_id: str,
    sessions: list[tuple[datetime, datetime]],
) -> tuple[int, list[dict[str, Any]]]:
    """Add the sessions; the refused ones (overlaps) are listed back."""
    stored, refused = 0, []
    for start, end in sessions:
        fields = {"start_at": start, "end_at": end, "note": ""}
        try:
            await work.add(session, user_id, fields, "import")
            stored += 1
        except InvalidInputError as exc:
            refused.append({"at": start.isoformat(), "reason": str(exc)})
    return stored, refused


def _report(
    sessions: list[tuple[datetime, datetime]],
    skipped: list[dict[str, Any]],
    tz: Any,
    dry_run: bool,
    stored: int,
) -> dict[str, Any]:
    """What was found (and stored): counts, hours, days, a preview."""
    local = [(s.astimezone(tz), e.astimezone(tz)) for s, e in sessions]
    hours = sum((e - s).total_seconds() for s, e in local) / 3600
    return {
        "dry_run": dry_run,
        "sessions": len(local),
        "stored": stored,
        "days": len({s.date() for s, _ in local}),
        "first_day": min((s.date() for s, _ in local), default=None),
        "last_day": max((s.date() for s, _ in local), default=None),
        "total_hours": round(hours, 2),
        "preview": [
            {"day": s.date(), "start": f"{s:%H:%M}", "end": f"{e:%H:%M}"}
            for s, e in local[:10]
        ],
        "skipped_count": len(skipped),
        "skipped": skipped[:MAX_SKIPPED],
    }


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
