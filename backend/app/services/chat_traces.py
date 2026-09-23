"""A WhatsApp chat as proofs, day by day (see :mod:`chat_read`).

For each day of the chat:

- your messages and the calls answered are work activity (« Activité
  pro »), from the first to the last (a call's end) — a message at 23:10
  or a 40 min call at 22:00 says you were at it;
- a day with only messages received is a proof « SMS / message »;
- calls (voice, video, missed) are also a proof « Appel », counted,
  with their total length;

each listing the day's messages (time, who, text). The export itself
is kept once, untouched, as a document (its SHA-256 in the report).
Who you are in the chat: « Moi » / « Me » / « Vous »…, else the chosen
name, else the most active sender who is not the chat's name.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.services import chat_read
from app.services.chat_read import Chat, Message
from app.services.trace_model import Trace

_ME = ("moi", "me", "you", "vous", "yo", "ich", "io", "eu")
_MINUTE = timedelta(minutes=1)
_LONGEST = 8000
_TEXT = "text/plain; charset=utf-8"


def traces(
    data: bytes, name: str, person: str, tz: ZoneInfo
) -> tuple[list[Trace], dict[str, Any]]:
    """The chat's traces (per day) and its original file; what was read."""
    chat = chat_read.read(data, name, tz)
    me = _me(chat, person)
    days: dict[date, list[Message]] = defaultdict(list)
    for message in chat.messages:
        days[message.at.astimezone(tz).date()].append(message)
    found = [
        t for day in sorted(days) for t in _day(chat.name, days[day], me, tz)
    ]
    if chat.messages:
        found.append(_original(chat, (name, data), tz))
    mine = sum(1 for m in chat.messages if m.who == me and not m.call)
    about = {
        "chat": f"WhatsApp — {chat.name} : {len(chat.messages)} messages "
        f"({mine} de vous) sur {len(days)} jours",
        "person": me,
        "people": [{"name": n, "actions": c} for n, c in chat.senders[:15]],
    }
    return found, about


def _me(chat: Chat, person: str) -> str:
    """Who you are: the name chosen, « Moi »…, else the most active."""
    names = [who for who, _ in chat.senders]
    if person.strip() in names:
        return person.strip()
    mine = next((n for n in names if n.lower() in _ME), None)
    others = [n for n in names if n != chat.name]
    return mine or (others or names or [""])[0]


def _day(
    chat: str, messages: list[Message], me: str, tz: ZoneInfo
) -> list[Trace]:
    """A day of the chat: my activity (or messages received), calls.

    My activity runs from my first message or call answered to my last
    one (a 40 min call at 22:00: until 22:40).
    """
    mine = [m for m in messages if m.who == me and not m.call]
    theirs = [m for m in messages if m.who != me and not m.call]
    calls = [m for m in messages if m.call]
    talks = [c for c in calls if c.seconds]
    listing = _listing(messages, tz)
    out = []
    if mine or talks:
        said = ", ".join(_said(mine, theirs, talks))
        active = sorted(mine + talks, key=lambda m: m.at)
        out.append(_trace(chat, "activite", active, said, listing))
    elif theirs:
        said = _count(len(theirs), "message") + " reçu"
        said += "s" if len(theirs) > 1 else ""
        out.append(_trace(chat, "sms", theirs, said, listing))
    if calls:
        out.append(
            _trace(chat, "appel", calls, _calls(calls), _listing(calls, tz))
        )
    return out


def _said(
    mine: list[Message], theirs: list[Message], talks: list[Message]
) -> list[str]:
    """« 3 messages de moi », « 2 reçus », « 1 appel (40 min) »."""
    parts = [_count(len(mine), "message") + " de moi"] if mine else []
    parts += [_count(len(theirs), "reçu")] if theirs else []
    if talks:
        length = _duration(sum(t.seconds for t in talks))
        parts.append(f"{_count(len(talks), 'appel')} ({length})")
    return parts


def _calls(calls: list[Message]) -> str:
    """« 3 appels (1 manqué), 45 min »."""
    missed = sum(1 for c in calls if not c.seconds)
    said = _count(len(calls), "appel")
    said += f" ({_count(missed, 'manqué')})" if missed else ""
    total = sum(c.seconds for c in calls)
    return said + (f", {_duration(total)}" if total else "")


def _trace(
    chat: str, kind: str, messages: list[Message], said: str, listing: str
) -> Trace:
    """One kind of the day: first → last (a call's end), the listing."""
    first = messages[0].at
    last = max(m.at + timedelta(seconds=m.seconds) for m in messages)
    return Trace(
        start=first,
        end=last if last - first >= _MINUTE else None,
        time_known=True,
        kind=kind,
        place=f"WhatsApp — {chat}"[:300],
        vendor=f"WhatsApp — {chat} : {said}"[:200],
        amount=None,
        currency="EUR",
        what=listing,
        group=f"whatsapp:{chat}:{first:%Y%m%d}:{kind}",
        actions=len(messages),
        daily=True,
    )


def _original(chat: Chat, file: tuple[str, bytes], tz: ZoneInfo) -> Trace:
    """The export, kept once as it was received (a document)."""
    first, last = chat.messages[0].at, chat.messages[-1].at
    span = f"{first.astimezone(tz):%d/%m/%Y} → {last.astimezone(tz):%d/%m/%Y}"
    return Trace(
        start=last,
        end=None,
        time_known=True,
        kind="document",
        place=f"WhatsApp — {chat.name}"[:300],
        vendor=f"WhatsApp — {chat.name} : export d'origine ({span})"[:200],
        amount=None,
        currency="EUR",
        what=f"{len(chat.messages)} messages, fichier d'origine intact",
        group=file[0],
        file=(file[0], _TEXT, file[1]),
    )


def _listing(messages: list[Message], tz: ZoneInfo) -> str:
    """One « 21:56 Alex : Bonjour » line a message (8000 characters)."""
    lines: list[str] = []
    size = 0
    for number, m in enumerate(messages):
        text = m.text.replace("\n", " / ")[:300]
        line = f"{m.at.astimezone(tz):%H:%M} {m.who} : {text}"
        if size + len(line) > _LONGEST - 40:
            lines.append(f"… et {len(messages) - number} messages de plus")
            break
        lines.append(line)
        size += len(line) + 1
    return "\n".join(lines)


def _duration(seconds: int) -> str:
    """« 3 min », « 1 h 05 »."""
    if seconds >= 3600:  # noqa: PLR2004
        return f"{seconds // 3600} h {seconds % 3600 // 60:02d}"
    return f"{max(1, round(seconds / 60))} min"


def _count(n: int, word: str) -> str:
    """« 1 message », « 3 messages »."""
    return f"{n} {word}{'s' if n > 1 else ''}"
