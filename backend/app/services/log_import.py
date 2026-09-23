"""Import one-event-per-line logs: work, water, cigarettes, coffee, pee.

Shortcut logs hold one time stamp per line (``12 | 13/05/2025 07:42``);
what they count is the file itself — the same keys as the one-tap rule
(``/sync/tally``). The key is taken from the file name when not given:

* ``work.start`` / ``work.end`` (Embauche / Débauche): imported together
  and paired into sessions (:func:`work_parse.pair`), nothing dropped;
* ``elimination.urination`` (Pipi): one timed entry per line, a time
  already stored is not added twice;
* counters (Eau, Cigarettes, Café, Envies): counted per local day; a day
  with no value gets the count, a day already holding one keeps the
  larger of the two (never added up twice, never lowered).
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import log_counters, urination, work_import, work_parse
from app.services.daily_rollup import user_zone
from app.services.work_parse import Event

#: File-name words → key (checked in order: "débauche" before "embauche").
NAME_KEYS = (
    (("debauche", "depart", "sortie"), "work.end"),
    (("embauche", "arrivee", "entree"), "work.start"),
    (("pipi", "urin", "miction"), "elimination.urination"),
    (("cigarette", "clope", "tabac"), "habit.cigarettes"),
    (("envie",), "habit.urges_broken"),
    (("cafe", "coffee"), "habit.coffee"),
    (("eau", "water", "bouteille"), "water.bottles_1_5"),
)
WORK_KEYS = {"work.start": "in", "work.end": "out"}


def key_for(filename: str) -> str | None:
    """The key a file name points to (None when it says nothing)."""
    name = work_parse.fold(filename)
    return next(
        (key for words, key in NAME_KEYS if any(w in name for w in words)),
        None,
    )


async def import_logs(
    session: AsyncSession,
    user_id: str,
    files: list[tuple[str, str | None, bytes]],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Import ``(file name, key or None, content)`` files."""
    tz = await user_zone(session, user_id)
    report: dict[str, Any] = {"dry_run": dry_run, "files": []}
    work_events: list[Event] = []
    for name, given, data in files:
        key = given or key_for(name)
        stamps, skipped = _stamps(data, name, tz)
        report["files"].append(_file(name, key, stamps, skipped, tz))
        if key in WORK_KEYS:
            work_events += [Event(at, WORK_KEYS[key], 0) for at in stamps]
        elif key is not None:
            report[key] = await _events(
                session, user_id, key, stamps, tz, dry_run
            )
    if work_events:
        report["work"] = await _work(session, user_id, work_events, tz, dry_run)
    return report


async def _events(
    session: AsyncSession,
    user_id: str,
    key: str,
    stamps: list[datetime],
    tz: ZoneInfo,
    dry_run: bool,
) -> dict[str, Any]:
    """Pee entries or a daily counter from one file's time stamps."""
    if key == urination.SPEC.key:
        return await log_counters.pee(session, user_id, stamps, dry_run)
    per_day = Counter(at.astimezone(tz).date() for at in stamps)
    return await log_counters.counts(
        session, user_id, key, dict(per_day), dry_run
    )


async def _work(
    session: AsyncSession,
    user_id: str,
    events: list[Event],
    tz: ZoneInfo,
    dry_run: bool,
) -> dict[str, Any]:
    """Pair clock-ins and clock-outs into sessions (and store them)."""
    spans, notes = work_parse.pair(events, tz)
    stored, refused = 0, list[dict[str, Any]]()
    if not dry_run:
        stored, refused = await work_import.store(session, user_id, spans)
    return work_import.summary(spans, refused, notes, tz, stored, dry_run)


def _stamps(
    data: bytes, name: str, tz: ZoneInfo
) -> tuple[list[datetime], list[dict[str, Any]]]:
    """Every time stamp of a file (UTC) and the lines without one."""
    stamps: list[datetime] = []
    skipped: list[dict[str, Any]] = []
    for number, line in enumerate(work_import.lines_of(data, name), start=1):
        found = work_parse.stamps(line)
        if not found and any(ch.isdigit() for ch in line):
            skipped.append({"line": number, "text": line[:120]})
        for at in found:
            local = at if at.tzinfo else at.replace(tzinfo=tz)
            stamps.append(local.astimezone(UTC))
    return stamps, skipped


def _file(
    name: str,
    key: str | None,
    stamps: list[datetime],
    skipped: list[dict[str, Any]],
    tz: ZoneInfo,
) -> dict[str, Any]:
    """What one file holds."""
    days: list[date] = sorted({at.astimezone(tz).date() for at in stamps})
    return {
        "name": name,
        "key": key,
        "events": len(stamps),
        "days": len(days),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "skipped": skipped[: work_import.MAX_SKIPPED],
        "problem": None if key else "type inconnu : choisissez-le",
    }
