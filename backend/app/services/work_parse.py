"""Read clock-in / clock-out times out of free text (txt, csv, json lines).

Shortcuts and apps write these logs in many ways, so a line is read by
its parts rather than by a fixed layout:

* a date — ``2025-03-02``, ``02/03/2025`` (day first), ``2 mars 2025``,
  ``Mar 2, 2025`` — or an ISO date-time (``2025-03-02T08:12:00+01:00``);
* times — ``08:12``, ``8h12``, ``08:12:33``, ``8:12 PM``;
* words that say which is which — embauche / arrivée / entrée / début /
  in / start… and débauche / départ / sortie / fin / out / end…

Each time takes the word before it (else the one after it). Without any
word, two times on a line are a start and an end (four: two sessions).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import NamedTuple

MONTHS = {
    "janv": 1, "janvier": 1, "jan": 1, "january": 1,
    "fevr": 2, "fevrier": 2, "fev": 2, "feb": 2, "february": 2,
    "mars": 3, "mar": 3, "march": 3,
    "avr": 4, "avril": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "june": 6,
    "juil": 7, "juillet": 7, "jul": 7, "july": 7,
    "aout": 8, "aug": 8, "august": 8,
    "sept": 9, "septembre": 9, "sep": 9, "september": 9,
    "oct": 10, "octobre": 10, "october": 10,
    "nov": 11, "novembre": 11, "november": 11,
    "dec": 12, "decembre": 12, "december": 12,
}  # fmt: skip

_IN = (
    r"embauche|arrivee?s?|arrive[ds]?|entree|debut|prise de poste|"
    r"clock ?in|check ?in|badge ?in|in|start(?:ed)?|begin|arrival"
)
_OUT = (
    r"debauche|depart|sortie|fin|quitte|clock ?out|check ?out|"
    r"badge ?out|out|end(?:ed)?|leave|left|departure"
)
#: A duration, not a clock time: "total 8h30", "pause 00:45".
_SKIP = r"total|duree|temps|travaillee?s?|worked|duration|pause|break"
_WORD = re.compile(rf"\b(?:(?P<in>{_IN})|(?P<out>{_OUT})|(?P<skip>{_SKIP}))\b")
_ISO = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[t ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?"
    r"(Z|[+-]\d{2}:?\d{2})?"
)
_DATES = (
    re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b"),
    re.compile(r"\b(\d{1,2})(?:er)?\s+([a-z]{3,9})\.?\s+(\d{4})\b"),
    re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b"),
)
#: Index of each layout in ``_DATES``; a 2-digit year is 20xx.
_YMD, _DMY, _D_MONTH_Y = 0, 1, 2
_SHORT_YEAR = 2
_LAST_HOUR, _LAST_MINUTE = 23, 59
_TIME = re.compile(
    r"\b(\d{1,2})\s?[:h]\s?(\d{2})(?::(\d{2}))?(?:\s?([ap])\.?m\.?)?\b"
)


class Event(NamedTuple):
    """A clock-in (``in``) or clock-out (``out``) at a local time."""

    at: datetime
    kind: str
    line: int


def fold(text: str) -> str:
    """Lower case, accents removed (``Débauche`` → ``debauche``)."""
    plain = unicodedata.normalize("NFKD", text)
    return "".join(c for c in plain if not unicodedata.combining(c)).lower()


def read_line(text: str, number: int) -> tuple[list[Event], str | None]:
    """The events of one line, or why the line was not understood."""
    line = fold(text)
    stamps = [(m.start(), _iso(m)) for m in _ISO.finditer(line)]
    rest = _ISO.sub(lambda m: " " * len(m.group()), line)
    day = _date(rest)
    rest = _blank_dates(rest)
    times = [(m.start(), _time(day, m)) for m in _TIME.finditer(rest)]
    moments = sorted(stamps + [(p, t) for p, t in times if t is not None])
    if not moments:
        has_digits = any(ch.isdigit() for ch in line)
        return [], ("pas d'heure" if day and has_digits else None)
    if day is None and not stamps:
        return [], "pas de date"
    return _kinds(line, moments, number)


def _kinds(
    line: str, moments: list[tuple[int, datetime]], number: int
) -> tuple[list[Event], str | None]:
    """Give each time its kind from the nearest word (or its order)."""
    words = [(m.start(), m.lastgroup or "") for m in _WORD.finditer(line)]
    if not words:
        if len(moments) % 2:
            return [], "embauche ou débauche ? (aucun mot, heure seule)"
        return _pairs(moments, number), None
    events = []
    for place, at in moments:
        before = [kind for spot, kind in words if spot < place]
        kind = before[-1] if before else words[0][1]
        if kind != "skip":
            events.append(Event(at, kind, number))
    if not events:
        return [], "durée seule (ni embauche ni débauche)"
    return _next_day(events), None


def _pairs(moments: list[tuple[int, datetime]], number: int) -> list[Event]:
    """Times without words: start, end, start, end and so on."""
    events = [
        Event(at, "in" if index % 2 == 0 else "out", number)
        for index, (_, at) in enumerate(moments)
    ]
    return _next_day(events)


def _next_day(events: list[Event]) -> list[Event]:
    """An end earlier than its start on one line is the next day (night)."""
    fixed: list[Event] = []
    for event in events:
        start = next((e for e in reversed(fixed) if e.kind == "in"), None)
        late = event.kind == "out" and start and event.at <= start.at
        fixed.append(
            event._replace(at=event.at + timedelta(days=1)) if late else event
        )
    return fixed


def _iso(match: re.Match[str]) -> datetime:
    """An ISO date-time; with an offset it is kept aware."""
    y, mo, d, h, mi, s, zone = match.groups()
    at = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
    if zone:
        stamp = f"{at.isoformat()}{'+00:00' if zone == 'z' else zone}"
        return datetime.fromisoformat(stamp)
    return at


def _date(line: str) -> date | None:
    """The first date of a line, any of the usual layouts."""
    for index, pattern in enumerate(_DATES):
        for match in pattern.finditer(line):
            day = _build_date(index, match.groups())
            if day is not None:
                return day
    return None


def _build_date(index: int, parts: tuple[str, ...]) -> date | None:
    """A date from a pattern's parts (None if not a real date)."""
    a, b, c = parts
    try:
        if index == _YMD:
            return date(int(a), int(b), int(c))
        if index == _DMY:
            year = int(c) + (2000 if len(c) == _SHORT_YEAR else 0)
            return date(year, int(b), int(a))
        if index == _D_MONTH_Y:
            return date(int(c), MONTHS[b], int(a))
        return date(int(c), MONTHS[a], int(b))
    except (KeyError, ValueError):
        return None


def _blank_dates(line: str) -> str:
    """Hide the dates so their digits are not read as times."""
    for pattern in _DATES:
        line = pattern.sub(lambda m: " " * len(m.group()), line)
    return line


def _time(day: date | None, match: re.Match[str]) -> datetime | None:
    """A time on the line's day (None without a day or if impossible)."""
    hour, minute, second, half = match.groups()
    h = int(hour) % 12 + (12 if half == "p" else 0) if half else int(hour)
    if day is None or h > 23 or int(minute) > 59:  # noqa: PLR2004
        return None
    return datetime(
        day.year, day.month, day.day, h, int(minute), int(second or 0)
    )


def pair(
    events: list[Event],
) -> tuple[list[tuple[datetime, datetime]], list[dict[str, object]]]:
    """Clock-ins matched with the next clock-out (24 h at most).

    The events must all be aware (or all naive) date-times.
    """
    sessions: list[tuple[datetime, datetime]] = []
    skipped: list[dict[str, object]] = []
    start: Event | None = None
    unique = {(e.at, e.kind): e for e in events}  # a time logged twice
    for event in sorted(unique.values(), key=lambda e: (e.at, e.kind)):
        if event.kind == "in":
            if start is not None:
                skipped.append(_orphan(start, "embauche sans débauche"))
            start = event
            continue
        if start is None or not _fits(start.at, event.at):
            skipped.append(_orphan(event, "débauche sans embauche"))
        else:
            sessions.append((start.at, event.at))
        start = None
    if start is not None:
        skipped.append(_orphan(start, "embauche sans débauche"))
    return sessions, skipped


def _fits(start: datetime, end: datetime) -> bool:
    """Whether a start and an end make a believable session (≤ 24 h)."""
    return timedelta(0) < end - start <= timedelta(hours=24)


def _orphan(event: Event, reason: str) -> dict[str, object]:
    """A time that could not be paired, for the import report."""
    return {"line": event.line, "at": event.at.isoformat(), "reason": reason}
