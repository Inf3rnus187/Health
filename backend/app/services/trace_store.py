"""Store imported traces: add the new ones, merge the ones met again.

The same trace often comes twice: a line of the expense report (the day
only) and the receipt of that ride (its time, the PDF). Same kind, same
local day, same amount, and times equal or one unknown: it is one trace,
completed by what the second one brings (time, end, file). A delivery or
a meal bought can also be logged as a meal with its price.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.models.work import Evidence
from app.services import evidence, evidence_files, trace_import, traces
from app.services.daily_rollup import user_zone
from app.services.timed_entries import day_bounds, utc
from app.services.trace_model import Trace

MAX_LISTED = 50
#: Kinds kept as one trace a day (a day of tickets).
DAILY = {"activite"}
_SAME_TIME = timedelta(minutes=1)


async def import_traces(
    session: AsyncSession,
    user_id: str,
    files: list[tuple[str, str, bytes]],
    *,
    dry_run: bool,
    meals: bool,
    person: str = "",
) -> tuple[dict[str, Any], list[Meal]]:
    """Import ``(file name, kind, content)`` files; meals to read after.

    ``person``: whose actions to keep from a ticket export.
    """
    tz = await user_zone(session, user_id)
    report: dict[str, Any] = {"dry_run": dry_run, "files": []}
    logged: list[Meal] = []
    for name, kind, data in files:
        found, skipped, about = trace_import.read(data, name, kind, tz, person)
        counts = {"new": 0, "merged": 0, "duplicates": 0}
        for trace in found:
            state, meal = await _save(
                session, user_id, trace, tz, (dry_run, meals)
            )
            counts[state] += 1
            logged += [meal] if meal else []
        found_all = (found, skipped, counts)
        report["files"].append(
            _summary(name, kind, found_all, about, tz, dry_run)
        )
    return report, logged


async def _save(
    session: AsyncSession,
    user_id: str,
    trace: Trace,
    tz: ZoneInfo,
    flags: tuple[bool, bool],
) -> tuple[str, Meal | None]:
    """Add, merge or skip one trace: ``new``, ``merged`` or ``duplicates``."""
    dry_run, meals = flags
    match = await _match(session, user_id, trace, tz)
    if match is not None:
        if not _brings(match, trace):
            return "duplicates", None
        if not dry_run:
            _merge(match, trace)
        return "merged", None
    if dry_run:
        return "new", None
    row = await evidence.create(session, user_id, _fields(trace), trace.file)
    if meals and trace.kind in traces.MEAL_KINDS:
        return "new", await traces.add_meal(session, row, trace.what)
    return "new", None


async def _match(
    session: AsyncSession, user_id: str, trace: Trace, tz: ZoneInfo
) -> Evidence | None:
    """The stored trace this one is (same kind, day, amount, time)."""
    start, end = day_bounds(trace.start.astimezone(tz).date(), tz)
    rows = await session.execute(
        select(Evidence).where(
            Evidence.user_id == user_id,
            Evidence.kind == trace.kind,
            Evidence.occurred_at >= start,
            Evidence.occurred_at < end,
        )
    )
    return next((row for row in rows.scalars() if _same(row, trace)), None)


def _same(row: Evidence, trace: Trace) -> bool:
    """Whether a stored item of that kind and day is this trace.

    A day of tickets is the same whatever its times (a later export has
    more actions); a document, only with the same file.
    """
    if trace.kind in DAILY:
        return True
    if trace.kind in evidence.PROOFS:
        return trace.file is not None and row.sha256 == _sha(trace.file[2])
    same_amount = (row.amount is None and trace.amount is None) or (
        row.amount is not None
        and trace.amount is not None
        and abs(row.amount - trace.amount) < 0.005  # noqa: PLR2004
    )
    close = abs(utc(row.occurred_at) - trace.start) <= _SAME_TIME
    return same_amount and (close or not row.time_known or not trace.time_known)


def _brings(row: Evidence, trace: Trace) -> bool:
    """Whether a trace met again adds something (time, end, file, text)."""
    if trace.kind in DAILY:
        return trace.actions > (row.count or 1)
    return bool(
        (trace.time_known and not row.time_known)
        or (trace.end and not row.ended_at)
        or (trace.file and not row.file_path)
        or bool(_new_parts(row, trace))
    )


def _merge(row: Evidence, trace: Trace) -> None:
    """Complete a stored trace with what the new one brings."""
    if trace.kind in DAILY:  # the day seen again, with more actions
        row.occurred_at, row.ended_at = trace.start, trace.end
        row.description, row.count = trace.what, trace.actions
        row.title = trace.vendor[:200]
        return
    if trace.time_known and not row.time_known:
        row.occurred_at, row.time_known = trace.start, True
    if trace.end and not row.ended_at:
        row.ended_at = trace.end
    if trace.file and not row.file_path:
        evidence_files.attach(row, trace.file)
    added = _new_parts(row, trace)
    if added:
        row.description = " · ".join([row.description or "", *added]).strip(
            " ·"
        )[:8000]
    have = [p for p in (row.title or "").split(" — ") if p]
    extra = [p for p in trace.vendor.split(" — ") if p and p not in have]
    row.title = " — ".join(have + extra)[:200]


def _fields(trace: Trace) -> dict[str, Any]:
    """The evidence columns of a new trace."""
    label = evidence.KINDS.get(trace.kind, trace.kind)
    return {
        "occurred_at": trace.start,
        "time_known": trace.time_known,
        "ended_at": trace.end,
        "kind": trace.kind,
        "title": (trace.vendor or trace.place or label)[:200],
        "description": trace.what,
        "place": (trace.place or trace.vendor)[:300],
        "amount": trace.amount,
        "currency": trace.currency,
        "count": trace.actions,
    }


def _summary(
    name: str,
    kind: str,
    parts: tuple[list[Trace], list[dict[str, Any]], dict[str, int]],
    about: dict[str, Any],
    tz: ZoneInfo,
    dry_run: bool,
) -> dict[str, Any]:
    """What one file held and what became of it."""
    found, skipped, counts = parts
    days: list[date] = sorted({t.start.astimezone(tz).date() for t in found})
    return {
        "name": name,
        "kind": kind,
        "label": evidence.KINDS.get(kind, "Deviné"),
        "traces": len(found),
        **counts,
        "stored": 0 if dry_run else counts["new"] + counts["merged"],
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "total": round(sum(t.amount or 0 for t in found), 2),
        "columns": about,
        "preview": [_preview(t, tz) for t in found[:8]],
        "skipped_count": len(skipped),
        "skipped": skipped[:MAX_LISTED],
    }  # fmt: skip


def _preview(trace: Trace, tz: ZoneInfo) -> dict[str, Any]:
    """One trace for the preview."""
    local = trace.start.astimezone(tz)
    return {
        "day": local.date(),
        "time": f"{local:%H:%M}" if trace.time_known else None,
        "end": f"{trace.end.astimezone(tz):%d/%m %H:%M}" if trace.end else None,
        "kind": trace.kind,
        "title": trace.vendor or trace.place,
        "place": trace.place or trace.vendor,
        "amount": trace.amount,
        "what": trace.what[:300],
    }


def _new_parts(row: Evidence, trace: Trace) -> list[str]:
    """What a trace met again says that the stored one does not."""
    have = row.description or ""
    return [p for p in trace.what.split(" · ") if p.strip() and p not in have]


def _sha(data: bytes) -> str:
    """A file's SHA-256, as stored with the evidence."""
    return hashlib.sha256(data).hexdigest()
