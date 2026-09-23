"""Import absences from an HR export (Lucca, Figgo, a spreadsheet…).

Columns are found by their titles: start and end days (or one day per
row, merged into periods — a weekend between two leave days does not
split them), the kind (« Compte », « Type d'absence »: congés payés,
RTT, maladie…), the status (refused and cancelled rows are skipped, a
pending one is noted), the person (a manager's export: one person
kept), a comment. The kind decides the hub's absence: arrêt maladie,
accident du travail, maladie professionnelle, repos (RTT, récupération),
congés, else « autre ». An absence already recorded is not added twice.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from typing import Any, NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Absence
from app.services import absences, table_read, trace_columns, work_parse
from app.services.table_read import Row

#: Column → folded titles (exact first, then contained).
_TITLES = {
    "start": ("date de debut", "date debut", "debut", "du", "start date",
              "startdate", "start", "from", "date de depart"),
    "end": ("date de fin", "date fin", "fin", "au", "end date", "enddate",
            "end", "to", "date de retour"),
    "day": ("date", "jour", "day", "date de l'absence"),
    "kind": ("compte", "type d'absence", "type", "leaveaccount.name",
             "leave account", "account", "motif", "nature", "absence",
             "categorie", "code"),
    "status": ("statut", "etat", "status", "state"),
    "person": ("collaborateur", "salarie", "employe", "nom complet",
               "owner.name", "employee", "utilisateur", "user", "nom",
               "name"),
    "note": ("commentaire", "comment", "remarque", "note", "raison"),
}  # fmt: skip
#: Folded words of the kind → hub kind (the first match wins).
_KINDS = (
    (("maladie pro", "maladie professionnelle"), "maladie_pro"),
    (("accident",), "accident_travail"),
    (("maladie", "arret", "sick", "illness", "hospital"), "arret_maladie"),
    (("rtt", "repos", "recup", "compensat", "jrtt", "non travaille",
      "rest", "off", "pont", "forfait"), "repos"),
    (("conge", "cp", "vacance", "holiday", "vacation", "leave", "pto",
      "sans solde", "paternite", "maternite", "parental", "familial",
      "evenement", "mariage", "deces", "demenagement", "enfant malade"),
     "conge"),
)  # fmt: skip
_PENDING = re.compile(r"attente|pending|a valider|soumis|submitted|waiting")
#: Worked time an HR tool also lists: not an absence.
_WORKED = re.compile(
    r"teletravail|remote|home ?office|formation|deplacement|mission"
)
_SHORT = 3
MAX_LISTED = 50


class Period(NamedTuple):
    """An absence read from a file."""

    start: date
    end: date
    kind: str
    label: str  # the export's own name for it ("RTT", "Congés payés")
    note: str


def read(
    data: bytes, name: str, person: str = ""
) -> tuple[list[Period], list[dict[str, Any]], dict[str, Any]]:
    """The periods of a file, the rows left out, the columns and people."""
    rows = table_read.rows_of(data, name)
    cols = _columns(rows)
    if not rows or not ({"start", "day"} & cols.keys()):
        return [], [{"line": 1, "reason": "aucune colonne de date"}], cols
    people = _people(rows, cols)
    who = work_parse.fold(person or (people[0][0] if people else ""))
    found: list[Period] = []
    skipped: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=2):
        if cols.get("person") and work_parse.fold(row[cols["person"]]) != who:
            continue
        period, reason = _period(row, cols)
        if period is None:
            skipped.append({"line": number, "reason": reason})
        else:
            found.append(period)
    about: dict[str, Any] = {
        **cols,
        "person": person or (people[0][0] if people else ""),
    }
    about["people"] = [{"name": n, "rows": c} for n, c in people[:15]]
    return _merged(found), skipped, about


def kind_of(text: str) -> str:
    """The hub's kind for an export's absence name ("RTT" → repos)."""
    plain = work_parse.fold(text)
    for words, kind in _KINDS:
        if any(re.search(rf"\b{re.escape(w)}", plain) for w in words):
            return kind
    return "autre"


def _columns(rows: list[Row]) -> dict[str, str]:
    """The absence columns found."""
    heads = {work_parse.fold(h): h for h in (rows[0] if rows else {})}
    found: dict[str, str] = {}
    for key, names in _TITLES.items():
        exact = next((heads[n] for n in names if n in heads), None)
        near = next(
            (
                h
                for n in names
                for f, h in heads.items()
                if len(n) > _SHORT and n in f and h not in found.values()
            ),
            None,
        )
        if exact or near:
            found[key] = exact or near or ""
    return found


def _people(rows: list[Row], cols: dict[str, str]) -> list[tuple[str, int]]:
    """The people of a manager's export, most rows first."""
    if not cols.get("person"):
        return []
    names = Counter(r[cols["person"]].strip() for r in rows)
    return [(n, c) for n, c in names.most_common() if n]


def _period(row: Row, cols: dict[str, str]) -> tuple[Period | None, str]:
    """A row as a period, or why it is left out."""
    status = work_parse.fold(row.get(cols.get("status", ""), ""))
    if trace_columns.CANCELLED.search(status):
        return None, "refusée ou annulée"
    first = _day(row.get(cols.get("start") or cols.get("day", ""), ""))
    last = _day(row.get(cols.get("end", ""), "")) or first
    if first is None or last is None or last < first:
        return None, "dates illisibles"
    label = row.get(cols.get("kind", ""), "").strip()
    if _WORKED.search(work_parse.fold(label)):
        return None, "temps travaillé (télétravail, formation…)"
    notes = [row.get(cols.get("note", ""), "").strip()]
    notes.append("en attente de validation" if _PENDING.search(status) else "")
    return Period(
        start=first,
        end=last,
        kind=kind_of(label),
        label=label[:100],
        note=" ; ".join(n for n in notes if n)[:500],
    ), ""


def _day(text: str) -> date | None:
    """A day in any writing (``02/04/2026``, ``2026-04-02T00:00:00``)."""
    day = work_parse.day_of(text)
    if day is None:
        stamps = work_parse.stamps(text)
        day = stamps[0].date() if stamps else None
    return day


def _merged(found: list[Period]) -> list[Period]:
    """Days of the same absence joined (a weekend between them too)."""
    out: list[Period] = []
    for p in sorted(found, key=lambda p: (p.kind, p.label, p.start)):
        last = out[-1] if out else None
        if (
            last
            and (last.kind, last.label) == (p.kind, p.label)
            and _joins(last.end, p.start)
        ):
            notes = " ; ".join(
                dict.fromkeys(n for n in (last.note, p.note) if n)
            )
            out[-1] = last._replace(end=max(last.end, p.end), note=notes)
        else:
            out.append(p)
    return sorted(out, key=lambda p: p.start)


def _joins(end: date, start: date) -> bool:
    """Whether ``start`` follows ``end`` (only a weekend between)."""
    day = end + timedelta(days=1)
    while day < start and day.weekday() >= 5:  # noqa: PLR2004
        day += timedelta(days=1)
    return start <= day


async def store(
    session: AsyncSession,
    user_id: str,
    files: list[tuple[str, bytes]],
    *,
    dry_run: bool,
    person: str = "",
) -> dict[str, Any]:
    """Import ``(file name, content)`` files; nothing twice."""
    report: dict[str, Any] = {"dry_run": dry_run, "files": []}
    for name, data in files:
        periods, skipped, about = read(data, name, person)
        counts = {"new": 0, "duplicates": 0}
        for period in periods:
            known = await _known(session, user_id, period)
            counts["duplicates" if known else "new"] += 1
            if not known and not dry_run:
                await absences.save(session, user_id, _fields(period))
        report["files"].append(_summary(name, periods, skipped, about, counts))
    return report


async def _known(session: AsyncSession, user_id: str, period: Period) -> bool:
    """Whether an absence of that kind already covers the period."""
    found = await session.execute(
        select(Absence.id).where(
            Absence.user_id == user_id,
            Absence.kind == period.kind,
            Absence.start_date <= period.start,
            Absence.end_date >= period.end,
        )
    )
    return found.first() is not None


def _fields(period: Period) -> dict[str, Any]:
    """The absence columns of a period."""
    source = f"Import : {period.label}" if period.label else "Import"
    return {
        "start_date": period.start,
        "end_date": period.end,
        "kind": period.kind,
        "cause": period.label if period.kind == "autre" else "",
        "note": " ; ".join(p for p in (source, period.note) if p)[:2000],
    }


def _summary(
    name: str,
    periods: list[Period],
    skipped: list[dict[str, Any]],
    about: dict[str, Any],
    counts: dict[str, int],
) -> dict[str, Any]:
    """What one file held and what became of it."""
    return {
        "name": name,
        "periods": len(periods),
        **counts,
        "days": sum((p.end - p.start).days + 1 for p in periods),
        "columns": about,
        "preview": [
            {**p._asdict(), "label_hub": absences.KINDS[p.kind]}
            for p in periods[:MAX_LISTED]
        ],
        "skipped_count": len(skipped),
        "skipped": skipped[:MAX_LISTED],
    }
