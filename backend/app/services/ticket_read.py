"""Work activity from a ticketing export (NinjaOne…): who acted, when.

A ticket export lists each ticket, then its comments: who wrote it, when,
and when that piece of work started. The comments you wrote are your
activity, timed by the tool: one trace per day, from the first to the
last action, each action listed (time, ticket, subject). A comment
written at 23:10 says you were working then — a fact for the days to
complete and the late days. Only the chosen person's actions are kept.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.services import work_parse
from app.services.table_read import Row

#: Column → folded titles, the first found wins (exact, then contained).
_TITLES = {
    "author": ("utilisateur de commentaires", "utilisateur de commentaire",
               "comment user", "comment author", "auteur du commentaire"),
    "created": ("commentaire cree", "comment created", "date du commentaire",
                "comment date"),
    "started": ("heure de debut du commentaire", "comment start time",
                "comment start"),
    "ticket": ("id", "ticket", "ticket id", "numero", "n°"),
    "subject": ("objet", "subject", "titre", "title", "sujet"),
    "visibility": ("visibilite de commentaires", "visibilite",
                   "comment visibility", "visibility"),
}  # fmt: skip
#: Titles this short ("id") must match exactly.
_SHORT = 3
#: A comment's start further back than this is not its work time.
_MAX_WORK = timedelta(hours=12)


class Day(NamedTuple):
    """One day of the person's actions (UTC times)."""

    day: date
    first: datetime
    last: datetime
    actions: list[str]


def columns(rows: list[Row]) -> dict[str, str]:
    """The ticket columns found (``author`` and ``created`` at least)."""
    heads = list(rows[0]) if rows else []
    found: dict[str, str] = {}
    for key, names in _TITLES.items():
        folded = {work_parse.fold(h): h for h in heads}
        exact = next((folded[n] for n in names if n in folded), None)
        near = next(
            (
                h
                for n in names
                for f, h in folded.items()
                if len(n) > _SHORT and n in f
            ),
            None,
        )
        if exact or near:
            found[key] = exact or near or ""
    return found if {"author", "created"} <= found.keys() else {}


def people(rows: list[Row], cols: dict[str, str]) -> list[tuple[str, int]]:
    """Who wrote comments, most active first."""
    authors = Counter(
        r[cols["author"]].strip()
        for r in rows
        if r.get(cols["author"], "").strip() and r.get(cols["created"])
    )
    return authors.most_common()


def days(
    rows: list[Row], cols: dict[str, str], person: str, tz: ZoneInfo
) -> list[Day]:
    """The person's actions, one entry per local day, in order."""
    who = work_parse.fold(person).strip()
    per_day: dict[date, list[tuple[datetime, datetime, str]]] = {}
    ticket = subject = ""
    for row in rows:
        if row.get(cols.get("ticket", ""), "").strip():
            ticket = row[cols["ticket"]].strip()
            subject = row.get(cols.get("subject", ""), "").strip()
        author = work_parse.fold(row.get(cols["author"], "")).strip()
        action = _action(row, cols, tz) if author == who else None
        if action is not None:
            start, at = action
            text = _text(
                start, at, f"#{ticket} {subject[:60]}".strip(), row, cols
            )
            per_day.setdefault(start.date(), []).append((start, at, text))
    return [_day(day, found) for day, found in sorted(per_day.items())]


def _action(
    row: Row, cols: dict[str, str], tz: ZoneInfo
) -> tuple[datetime, datetime] | None:
    """When a comment's work started and when it was written (local)."""
    written = _local(row.get(cols["created"], ""), tz)
    if written is None:
        return None
    started = _local(row.get(cols.get("started", ""), ""), tz)
    if started is None or not timedelta(0) <= written - started <= _MAX_WORK:
        started = written
    return started, written


def _local(text: str, tz: ZoneInfo) -> datetime | None:
    """A cell's date-time in the user's zone (exports use local time)."""
    found = work_parse.stamps(text)
    if not found:
        return None
    at = found[0]
    return at.astimezone(tz) if at.tzinfo else at.replace(tzinfo=tz)


def _text(
    start: datetime, at: datetime, what: str, row: Row, cols: dict[str, str]
) -> str:
    """One action as ``08:12–08:40 #1390 Subject (privé)``."""
    span = f"{start:%H:%M}" + (
        f"–{at:%H:%M}" if at - start >= timedelta(minutes=1) else ""
    )
    private = work_parse.fold(row.get(cols.get("visibility", ""), ""))
    return f"{span} {what}" + (" (privé)" if private.startswith("priv") else "")


def _day(day: date, found: list[tuple[datetime, datetime, str]]) -> Day:
    """A day's actions in time order."""
    found.sort()
    return Day(
        day=day,
        first=found[0][0].astimezone(UTC),
        last=max(at for _, at, _ in found).astimezone(UTC),
        actions=[text for *_, text in found],
    )
