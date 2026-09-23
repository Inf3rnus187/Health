"""The most significant days of a period: what stands out, and why.

From the day-by-day table of the work ↔ health file: a session run
through the night (24 h or more), an amplitude over 13 h (the 11 h of
daily rest cannot fit), more than 10 h of work, a Saturday, Sunday or
public holiday worked, work during an absence, an end after 21:00 —
with the notes typed on the day's sessions. The most striking first:
continuous sessions, days off worked, then the longest spans.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services import absences, work_legal
from app.services.work_math import clock_text

LIMIT = 20
_CONTINUOUS = 24.0
_REST = 13.0
_MAX_DAY = 10.0
_LATE = 21.0
_MIDNIGHT = 24.0
_WEEKEND = {5: "samedi travaillé", 6: "dimanche travaillé"}


def significant(
    table: list[dict[str, Any]], limit: int = LIMIT
) -> list[dict[str, Any]]:
    """The days that stand out, the most striking first."""
    years = {row["date"].year for row in table}
    feasts = {d for y in years for d in work_legal.holidays(y)}
    found = []
    for row in table:
        if row["start"] is None or row["end"] is None:
            continue
        flags = _flags(row, feasts)
        if flags:
            found.append(_line(row, flags))
    found.sort(key=lambda r: (-r["score"], r["date"]))
    return found[:limit]


def _flags(row: dict[str, Any], feasts: set[date]) -> list[str]:
    """Why a day stands out (nothing: an ordinary day)."""
    span = row["end"] - row["start"]
    hours = row["hours"] or 0.0
    flags = []
    if span >= _CONTINUOUS:
        flags.append(f"session continue de {hm(span)}, nuit comprise")
    elif span > _REST:
        flags.append(f"amplitude {hm(span)} > 13 h (repos de 11 h impossible)")
    if hours > _MAX_DAY and span < _CONTINUOUS:
        flags.append(f"{hm(hours)} de travail > 10 h")
    flags.append(_WEEKEND.get(row["weekday"], ""))
    flags.append("jour férié travaillé" if row["date"] in feasts else "")
    if row["absence"]:
        label = absences.KINDS.get(row["absence"], row["absence"])
        flags.append(f"travaillé pendant : {label.lower()}")
    if row["end"] >= _LATE and span < _CONTINUOUS:
        flags.append(
            "fin après minuit" if row["end"] >= _MIDNIGHT else "fin après 21 h"
        )
    return [f for f in flags if f]


def _line(row: dict[str, Any], flags: list[str]) -> dict[str, Any]:
    """One significant day: arrival, departure, amplitude, why."""
    span = row["end"] - row["start"]
    off = row["weekday"] >= 5 or any("férié" in f for f in flags)  # noqa: PLR2004
    score = (
        span + 8 * (span >= _CONTINUOUS) + 5 * off + 5 * bool(row["absence"])
    )
    return {
        "date": row["date"],
        "weekday": row["weekday"],
        "arrival": clock_text(row["start"]),
        "departure": clock_text(row["end"]),
        "amplitude": round(span, 2),
        "hours": row["hours"],
        "remote": row.get("remote"),
        "flags": flags,
        "notes": row.get("notes", []),
        "score": round(score, 2),
    }


def hm(hours: float) -> str:
    """« 33 h 21 »."""
    minutes = round(hours * 60)
    return f"{minutes // 60} h {minutes % 60:02d}"
