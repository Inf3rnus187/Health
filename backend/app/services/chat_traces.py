"""A WhatsApp chat as proofs, day by day (see :mod:`chat_read`).

For each day of the chat:

- your messages are work activity (« Activité pro »), from the first
  to the last one you sent — a message at 23:10 says you were at it;
- a day with only messages received is a proof « SMS / message »;
- calls (voice, video, missed) are a proof « Appel », counted;

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
    """A day of the chat: my activity (or messages received), calls."""
    mine = [m for m in messages if m.who == me and not m.call]
    theirs = [m for m in messages if m.who != me and not m.call]
    calls = [m for m in messages if m.call]
    listing = _listing(messages, tz)
    out = []
    if mine:
        said = _count(len(mine), "message") + " de moi"
        said += f", {_count(len(theirs), 'reçu')}" if theirs else ""
        out.append(_trace(chat, "activite", mine, said, listing))
    elif theirs:
        said = _count(len(theirs), "message") + " reçu"
        said += "s" if len(theirs) > 1 else ""
        out.append(_trace(chat, "sms", theirs, said, listing))
    if calls:
        said = _count(len(calls), "appel")
        out.append(_trace(chat, "appel", calls, said, _listing(calls, tz)))
    return out


def _trace(
    chat: str, kind: str, messages: list[Message], said: str, listing: str
) -> Trace:
    """One kind of the day: first → last, how many, the listing."""
    first, last = messages[0].at, messages[-1].at
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


def _count(n: int, word: str) -> str:
    """« 1 message », « 3 messages »."""
    return f"{n} {word}{'s' if n > 1 else ''}"
