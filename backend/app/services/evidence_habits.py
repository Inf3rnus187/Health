"""Habits as recorded: cigarettes, coffee, water, urges broken, pees.

For a report that must prove what was recorded — per counter over the
period: days of the period, days with a value, days **without** one (a
day without an entry is not a day at zero: « 0 aujourd'hui » records an
explicit zero), total, mean per recorded day, median, lowest and highest
days (with their date), per month (per week for two months or less);
and, with ``compare_from``, before / after that day (means, days, the
change in %).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition

#: Counter → its label in a report.
COUNTERS = {
    "habit.cigarettes": "Cigarettes",
    "habit.urges_broken": "Envies de fumer cassées",
    "habit.coffee": "Cafés",
    "water.bottles_1_5": "Eau (bouteilles de 1,5 L)",
    "elimination.urination": "Mictions",
}
_WEEKS_UP_TO = 62


async def habits(
    session: AsyncSession,
    user_id: str,
    span: tuple[date, date],
    compare_from: date | None = None,
) -> list[dict[str, Any]]:
    """Each counter's recorded facts over ``span`` (none: not listed)."""
    daily = await _daily(session, user_id, span)
    out = []
    for key, label in COUNTERS.items():
        values = daily.get(key, {})
        if not values:
            continue
        facts = {"key": key, "label": label, **stats(values, span)}
        facts["periods"] = _periods(values, span)
        facts["series"] = [
            [d.isoformat(), v] for d, v in sorted(values.items())
        ]
        if compare_from and span[0] < compare_from <= span[1]:
            facts["compare"] = compare(values, span, compare_from)
        out.append(facts)
    return out


def stats(values: dict[date, float], span: tuple[date, date]) -> dict[str, Any]:
    """Days with / without a value, total, mean, median, lowest, highest."""
    days = (span[1] - span[0]).days + 1
    inside = {d: v for d, v in values.items() if span[0] <= d <= span[1]}
    if not inside:
        return {"days": days, "days_with_data": 0, "days_without": days}
    low = min(inside, key=lambda d: (inside[d], d))
    high = max(inside, key=lambda d: (inside[d], d))
    return {
        "days": days,
        "days_with_data": len(inside),
        "days_without": days - len(inside),
        "total": round(sum(inside.values()), 1),
        "mean": round(sum(inside.values()) / len(inside), 1),
        "median": round(median(inside.values()), 1),
        "lowest": {"value": inside[low], "date": low.isoformat()},
        "highest": {"value": inside[high], "date": high.isoformat()},
    }


def compare(
    values: dict[date, float], span: tuple[date, date], split: date
) -> dict[str, Any]:
    """Before ``split`` and from it: each part's facts, the mean's change."""
    before = stats(values, (span[0], split - timedelta(days=1)))
    after = stats(values, (split, span[1]))
    change = None
    if before.get("mean") and after.get("mean") is not None:
        change = round(
            (after["mean"] - before["mean"]) / before["mean"] * 100, 1
        )
    return {"split": split.isoformat(), "before": before, "after": after,
            "change_pct": change}  # fmt: skip


def _periods(
    values: dict[date, float], span: tuple[date, date]
) -> list[dict[str, Any]]:
    """Per week (≤ 62 days) or per month: days with data, mean, total."""
    weekly = (span[1] - span[0]).days + 1 <= _WEEKS_UP_TO
    groups: dict[date, list[float]] = {}
    day = span[0]
    while day <= span[1]:
        start = (
            day - timedelta(days=day.weekday())
            if weekly
            else day.replace(day=1)
        )
        group = groups.setdefault(start, [])
        if day in values:
            group.append(values[day])
        day += timedelta(days=1)
    unit = "week" if weekly else "month"
    return [_period(start, unit, group) for start, group in groups.items()]


def _period(start: date, unit: str, group: list[float]) -> dict[str, Any]:
    """One week or month."""
    return {
        "start": start.isoformat(),
        "unit": unit,
        "days_with_data": len(group),
        "mean": round(sum(group) / len(group), 1) if group else None,
        "total": round(sum(group), 1),
    }


async def _daily(
    session: AsyncSession, user_id: str, span: tuple[date, date]
) -> dict[str, dict[date, float]]:
    """Each counter's daily value over the span."""
    rows = await session.execute(
        select(
            MetricDefinition.key, Measurement.date_key, Measurement.value_num
        )
        .join(MetricDefinition, MetricDefinition.id == Measurement.metric_id)
        .where(
            Measurement.user_id == user_id,
            MetricDefinition.key.in_(COUNTERS),
            Measurement.date_key.between(span[0], span[1]),
            Measurement.event_id.is_(None),
            Measurement.value_num.is_not(None),
        )
    )
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for key, day, value in rows:
        out[key][day] = float(value)
    return out
