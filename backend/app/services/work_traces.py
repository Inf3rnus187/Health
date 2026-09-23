"""Traces and expenses in the work ↔ health file (pure).

Traces are what third parties saw: a transport pass validated, a taxi,
a parking ticket, a delivery, a hotel night, an expense report. They
back the clocked hours (and show presence on days never clocked), and
their amounts show what long days cost — delivered meals included,
with the AI's score of each meal.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, time
from statistics import fmean
from typing import Any
from zoneinfo import ZoneInfo

from app.models.work import Evidence
from app.services import evidence, work_corr
from app.services.timed_entries import utc
from app.services.traces import MEAL_KINDS

#: A trace at or after this hour on a working day is "late".
LATE = time(21, 0)
#: Traces that place you somewhere (not a meal, not a document).
PRESENCE = {"transport", "taxi", "parking", "hotel"}
_LONG_DAY_H = 10.0


def per_day(
    items: list[Evidence], tz: ZoneInfo
) -> dict[date, list[dict[str, Any]]]:
    """The traces of each local day, in time order."""
    days: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for item in sorted(items, key=lambda e: utc(e.occurred_at)):
        if item.kind not in evidence.TRACES:
            continue
        start = utc(item.occurred_at).astimezone(tz)
        end = utc(item.ended_at).astimezone(tz) if item.ended_at else None
        days[start.date()].append(
            {
                "kind": item.kind,
                "time": f"{start:%H:%M}",
                "end": f"{end:%H:%M}" if end else None,
                "late": start.time() >= LATE,
                "place": item.place,
                "amount": item.amount,
                "meal_id": item.meal_id,
            }
        )
    return days


def summary(
    table: list[dict[str, Any]], scores: dict[str, float]
) -> dict[str, Any]:
    """Counts, amounts, late traces, unclocked presence, deliveries."""
    pairs = [(r, t) for r in table for t in r["traces"]]
    kinds: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for _, trace in pairs:
        kinds[trace["kind"]].append(trace)
    return {
        "by_kind": [_kind(k, v) for k, v in sorted(kinds.items())],
        "late": [_late(r, t) for r, t in pairs if t["late"] and r["worked"]],
        "unclocked_days": [r["date"] for r in table if _unclocked(r)],
        "months": _months(table),
        "deliveries": _deliveries(table, scores),
    }


def _kind(kind: str, found: list[dict[str, Any]]) -> dict[str, Any]:
    """Count and total of one kind."""
    total = round(sum(t["amount"] or 0 for t in found), 2)
    label = evidence.TRACES[kind]
    return {"kind": kind, "label": label, "count": len(found), "total": total}


def _late(row: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    """A late trace on a working day."""
    return {
        "date": row["date"],
        "time": trace["time"],
        "kind": trace["kind"],
        "place": trace["place"],
    }


def _unclocked(row: dict[str, Any]) -> bool:
    """A day never clocked where a trace places you somewhere."""
    return not row["worked"] and any(
        t["kind"] in PRESENCE for t in row["traces"]
    )


def _months(table: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Amounts per month and kind."""
    months: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for row in table:
        for trace in row["traces"]:
            months[f"{row['date']:%Y-%m}"][trace["kind"]] += (
                trace["amount"] or 0
            )
    return [
        {
            "month": m,
            **{k: round(v, 2) for k, v in kinds.items()},
            "total": round(sum(kinds.values()), 2),
        }
        for m, kinds in sorted(months.items())
    ]


def _deliveries(
    table: list[dict[str, Any]], scores: dict[str, float]
) -> dict[str, Any]:
    """Meals delivered / bought: when, how much, how healthy."""
    meals = [
        (r, t) for r in table for t in r["traces"] if t["kind"] in MEAL_KINDS
    ]
    long_days = [(r, t) for r, t in meals if _long(r)]
    rated = [scores[t["meal_id"]] for _, t in meals if t["meal_id"] in scores]
    spend = [
        (r["hours"], _spent(r))
        for r in table
        if r["hours"] and not r["partial"]
    ]
    return {
        "orders": len(meals),
        "total": round(sum(t["amount"] or 0 for _, t in meals), 2),
        "late": sum(1 for _, t in meals if t["late"]),
        "on_long_days": len(long_days),
        "long_days_total": round(
            sum(t["amount"] or 0 for _, t in long_days), 2
        ),
        "avg_score": round(fmean(rated), 1) if rated else None,
        "hours_vs_spend": work_corr.pearson(
            [h for h, _ in spend], [s for _, s in spend]
        ),
    }


def _long(row: dict[str, Any]) -> bool:
    """A day over 10 h, or ending at 21:00 or later."""
    hours, end = row["hours"] or 0, row["end"] or 0
    return hours > _LONG_DAY_H or end >= LATE.hour


def _spent(row: dict[str, Any]) -> float:
    """What a day's delivered / bought meals cost."""
    return sum(
        t["amount"] or 0 for t in row["traces"] if t["kind"] in MEAL_KINDS
    )
