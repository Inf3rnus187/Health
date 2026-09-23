"""Days off in the work numbers: which days, and why.

A day is off when an absence covers it — arrêt maladie, accident du
travail and maladie professionnelle count as « arrêt », then congés,
repos (RTT, récupération), autre — or when it is a public holiday on a
weekday. Averages and the contract target leave those days out: a week
with two days of sick leave is not a short week of work.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Absence
from app.services import absences, work_legal

#: Absence kind → group shown in the numbers.
GROUPS = {
    "arret_maladie": "arret",
    "accident_travail": "arret",
    "maladie_pro": "arret",
    "conge": "conge",
    "repos": "repos",
    "autre": "autre",
}
#: Group → French label (in the order they win when absences overlap).
LABELS = {
    "arret": "Arrêt (maladie, accident)",
    "conge": "Congés",
    "repos": "Repos (RTT, récupération)",
    "autre": "Autre absence",
    "ferie": "Jour férié",
}
_WEEKDAYS = 5
_LISTED = 12


def day_map(leaves: list[Absence], first: date, last: date) -> dict[date, str]:
    """Each day off between ``first`` and ``last`` with its group."""
    rank = list(LABELS)
    out: dict[date, str] = {}
    for leave in sorted(
        leaves, key=lambda a: rank.index(GROUPS.get(a.kind, "autre"))
    ):
        day, end = max(leave.start_date, first), min(leave.end_date, last)
        while day <= end:
            out.setdefault(day, GROUPS.get(leave.kind, "autre"))
            day += timedelta(days=1)
    for year in range(first.year, last.year + 1):
        for feast in work_legal.holidays(year):
            if first <= feast <= last and feast.weekday() < _WEEKDAYS:
                out.setdefault(feast, "ferie")
    return dict(sorted(out.items()))


async def days_off(
    session: AsyncSession, user_id: str, first: date, last: date
) -> dict[date, str]:
    """The user's days off between two days (absences, holidays)."""
    leaves = await absences.list_absences(session, user_id, first, last)
    return day_map(leaves, first, last)


def counts(off: dict[date, str]) -> list[dict[str, Any]]:
    """Days off per group: calendar days and weekdays."""
    days = Counter(off.values())
    weekdays = Counter(k for d, k in off.items() if d.weekday() < _WEEKDAYS)
    return [
        {
            "kind": kind,
            "label": label,
            "days": days[kind],
            "workdays": weekdays[kind],
        }
        for kind, label in LABELS.items()
        if days[kind]
    ]


def present_weekdays(off: dict[date, str], first: date, last: date) -> int:
    """Weekdays between two days that were not off."""
    total, day = 0, first
    while day <= last:
        total += day.weekday() < _WEEKDAYS and day not in off
        day += timedelta(days=1)
    return total


def texts(work: dict[str, Any]) -> list[str]:
    """The days-off lines of a report (French)."""
    parts = [
        f"{a['label']} {a['days']} j ({a['workdays']} ouvrés)"
        for a in work.get("absences", [])
    ]
    out = [
        f"Jours d'absence : {', '.join(parts)}."
        if parts
        else "Aucune absence ni jour férié dans la période.",
        "Heures au-delà du contrat, jours d'absence et fériés déduits de "
        f"l'objectif de la semaine : {work['beyond_target_hours']:g} h.",
    ]
    during = work["worked_while_off"]
    if during:
        days = ", ".join(f"{d['date']:%d/%m/%Y}" for d in during[:_LISTED])
        more = f" +{len(during) - _LISTED}" if len(during) > _LISTED else ""
        out.append(
            f"Jours travaillés pendant une absence : {len(during)} "
            f"({days}{more})."
        )
    return out
