"""WhatsApp chat exports (.txt): who wrote what, and when.

Both exports are read, in any language:

- iPhone: ``[23/05/2025 21:56:42] Alex : Bonjour`` (seconds, brackets);
- Android: ``23/05/2025 21:56 - Alex: Bonjour`` (and ``5/23/25, 9:56 PM``).

A line that does not start with a date continues the message before it.
The end-to-end encryption notice is left out (on the iPhone its sender
is the chat's name); a call (« Appel vocal 3 min », « Appel vocal
manqué », « Voice call ») is kept apart, with its length. Dates are
day first unless the file shows otherwise (a second number above 12);
times are the phone's, the user's local time.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import NamedTuple
from zoneinfo import ZoneInfo

_LINE = re.compile(
    r"^\[?(?P<date>\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),?\s+"
    r"(?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s?[AaPp]\.?\s?[Mm]\.?)?)"
    r"\]?\s*(?:-\s)?\s*(?P<rest>.*)$"
)
_WHO = re.compile(r"^(?P<who>[^:\n]{1,80}?)\s?:\s?(?P<text>.*)$", re.DOTALL)
_MARKS = "\u200e\u200f\u202a\u202c\ufeff"
_NOTICE = re.compile(
    r"chiffr[ée]s de bout en bout|end-to-end encrypted|"
    r"cifrados de extremo a extremo|ende-zu-ende",
    re.IGNORECASE,
)
_CALL = re.compile(
    r"^(appel (vocal|vid[ée]o)|voice call|video call|missed (voice|video) "
    r"call|appel manqu[ée])",
    re.IGNORECASE,
)
_MISSED = re.compile(r"manqu|missed|sans r[ée]ponse|no answer|refus|declin")
_HOURS = re.compile(r"(\d+)\s*(?:h|hr|hrs|heures?|hours?)\b", re.IGNORECASE)
_MINUTES = re.compile(r"(\d+)\s*min", re.IGNORECASE)
_SECONDS = re.compile(r"(\d+)\s*(?:s|sec|secondes?|seconds?)\b", re.IGNORECASE)
_FILE_NAME = re.compile(
    r"(?:discussion whatsapp avec|whatsapp chat with|whatsapp chat -)\s*"
    r"(?P<name>.+?)(?:\.txt|\.zip)?$",
    re.IGNORECASE,
)
_SAMPLE = 40


class Message(NamedTuple):
    """One message (UTC time); a call is flagged, with its length."""

    at: datetime
    who: str
    text: str
    call: bool
    #: How long a call lasted (« Appel vocal 3 min »); 0: missed, unknown.
    seconds: int = 0


class Chat(NamedTuple):
    """A chat: its name, messages in order, and who wrote how many."""

    name: str
    messages: list[Message]
    senders: list[tuple[str, int]]


def is_chat(data: bytes, name: str) -> bool:
    """Whether a file is a WhatsApp export (its first lines say so)."""
    if not name.lower().endswith(".txt"):
        return False
    head = _text(data[:4000]).splitlines()[:_SAMPLE]
    dated = [m for m in map(_LINE.match, map(_clean, head)) if m]
    said = [m for m in dated if _WHO.match(m["rest"])]
    return bool(said) and len(said) * 2 >= len(dated)


def read(data: bytes, name: str, tz: ZoneInfo) -> Chat:
    """The messages of an export, the chat's name and its senders."""
    raw = _raw(_text(data))
    day_first = _day_first([d for d, _, _ in raw])
    messages: list[Message] = []
    notice_by = ""
    for day, clock, rest in raw:
        at = _when(day, clock, day_first, tz)
        found = _WHO.match(rest)
        if at is None or found is None:
            continue  # a system line without a sender
        who, text = found["who"].strip(), _clean(found["text"]).strip()
        if _NOTICE.search(text):
            notice_by = notice_by or who
            continue
        call = bool(_CALL.match(text))
        length = _length(text) if call else 0
        messages.append(Message(at, who, text, call, length))
    senders = Counter(m.who for m in messages if not m.call).most_common()
    return Chat(_name(name, notice_by, senders), messages, senders)


def _length(text: str) -> int:
    """A call's length in seconds (« 1 h 5 min », « 45 s »); 0 if missed."""
    if _MISSED.search(text.lower()):
        return 0
    total = 0
    for pattern, unit in ((_HOURS, 3600), (_MINUTES, 60), (_SECONDS, 1)):
        found = pattern.search(text)
        total += int(found[1]) * unit if found else 0
    return total


def _raw(text: str) -> list[tuple[str, str, str]]:
    """(date, time, rest) per message, continuation lines joined."""
    out: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        found = _LINE.match(_clean(line))
        if found:
            out.append((found["date"], found["time"], found["rest"]))
        elif out and line.strip():
            day, clock, rest = out[-1]
            out[-1] = (day, clock, f"{rest}\n{_clean(line).strip()}")
    return out


def _day_first(dates: list[str]) -> bool:
    """Day before month, unless a second number above 12 says otherwise."""
    parts = [re.split(r"[./-]", d) for d in dates]
    if any(len(p[0]) != 4 and int(p[0]) > 12 for p in parts):  # noqa: PLR2004
        return True
    return not any(len(p[0]) != 4 and int(p[1]) > 12 for p in parts)  # noqa: PLR2004


def _when(
    day: str, clock: str, day_first: bool, tz: ZoneInfo
) -> datetime | None:
    """A message's time in UTC (its text is the phone's local time)."""
    year, month, date_ = _ymd(day, day_first)
    digits = [int(x) for x in re.findall(r"\d+", clock)]
    hour, minute, second = (digits + [0, 0])[:3]
    if re.search(r"[AaPp]\.?\s?[Mm]", clock):  # 12-hour clock
        hour = hour % 12 + (12 if re.search(r"[Pp]\.?\s?[Mm]", clock) else 0)
    try:
        local = datetime(year, month, date_, hour, minute, second, tzinfo=tz)
    except ValueError:
        return None
    return local.astimezone(UTC)


def _ymd(day: str, day_first: bool) -> tuple[int, int, int]:
    """Year, month, day of "23/05/2025", "5/23/25" or "2025-05-23"."""
    a, b, c = (int(x) for x in re.split(r"[./-]", day))
    if a > 999:  # noqa: PLR2004 - year first
        return a, b, c
    year = c + 2000 if c < 100 else c  # noqa: PLR2004
    return (year, b, a) if day_first else (year, a, b)


def _name(file: str, notice_by: str, senders: list[tuple[str, int]]) -> str:
    """The chat's name: from the file, the notice's sender, or senders."""
    found = _FILE_NAME.search(file.rsplit("/", 1)[-1])
    if found:
        return found["name"].strip()
    if notice_by:
        return notice_by
    return ", ".join(who for who, _ in senders[:3]) or "conversation"


def _text(data: bytes) -> str:
    """The file's text (UTF-8, else Latin-1)."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _clean(line: str) -> str:
    """A line without its invisible direction marks."""
    return line.translate({ord(c): None for c in _MARKS}).replace("\u202f", " ")
