"""Work ↔ health correlations (pure): per band of hours and per period.

Each day row joins the day's work (hours of complete sessions, first
clock-in, last clock-out) with the night after it (the night you wake up
from the next day) and the day's health values. Days with a missing
clock-in or clock-out are "partial": their hours are not used in the
bands nor in the correlation (they would bias them).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean
from typing import Any

#: Bands of worked hours for the night-after comparison.
BANDS = (
    ("Jour non travaillé", None, None),
    ("Moins de 8 h", 0.0, 8.0),
    ("8 h à 10 h", 8.0, 10.0),
    ("Plus de 10 h", 10.0, 99.0),
)
#: Health values averaged per period (key in the day row → label).
HEALTH = {
    "rest.hr": "FC repos",
    "heart.hrv": "VFC",
    "vitals.bp_systolic": "PA systolique",
    "activity.steps": "Pas",
    "habit.cigarettes": "Cigarettes",
    "habit.coffee": "Cafés",
}
_MIN_PAIRS = 5


def pearson(xs: list[float], ys: list[float]) -> dict[str, Any] | None:
    """Pearson's r of paired values (None under 5 pairs or no spread)."""
    if len(xs) < _MIN_PAIRS or len(xs) != len(ys):
        return None
    mx, my = fmean(xs), fmean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return {"r": round(cov / (vx * vy) ** 0.5, 3), "n": len(xs)}


def correlations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Hours worked / last clock-out against the night after."""
    nights = [r for r in rows if r["night"] and not r["partial"]]
    return {
        "hours_vs_sleep": pearson(*_pairs(nights, "hours", _sleep)),
        "hours_vs_awakenings": pearson(*_pairs(nights, "hours", _woke)),
        "end_vs_sleep": pearson(*_pairs(nights, "end", _sleep)),
    }


def _sleep(row: dict[str, Any]) -> float:
    """Hours asleep the night after."""
    return float(row["night"]["asleep_min"]) / 60


def _woke(row: dict[str, Any]) -> float | None:
    """Awakenings the night after."""
    value = row["night"]["awakenings"]
    return None if value is None else float(value)


def bands(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The nights after days off, short, normal and long days."""
    out = []
    for label, low, high in BANDS:
        chosen = [
            r for r in rows
            if r["night"] and not r["partial"] and _in_band(r, low, high)
        ]  # fmt: skip
        nights = [r["night"] for r in chosen]
        out.append(
            {
                "label": label,
                "nights": len(nights),
                "sleep_hours": _avg([n["asleep_min"] / 60 for n in nights]),
                "awakenings": _avg([n["awakenings"] for n in nights]),
                "blocks": _avg([n["blocks"] for n in nights]),
            }
        )
    return out


def periods(
    rows: list[dict[str, Any]], unit: str, contract: float
) -> list[dict[str, Any]]:
    """Weeks (``week``), months (``month``) or years (``year``)."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_key(row["date"], unit)].append(row)
    return [
        _period(key, group, unit, contract)
        for key, group in sorted(groups.items())
    ]


def _period(
    key: str, group: list[dict[str, Any]], unit: str, contract: float
) -> dict[str, Any]:
    """One period's work, sleep and health."""
    hours = sum(r["hours"] or 0 for r in group)
    nights = [r["night"] for r in group if r["night"]]
    weeks: dict[date, float] = defaultdict(float)
    for r in group:
        weeks[r["date"] - timedelta(days=r["date"].weekday())] += (
            r["hours"] or 0
        )
    return {
        "period": key,
        "days_worked": sum(1 for r in group if r["worked"]),
        "hours": round(hours, 2),
        "overtime": round(
            sum(max(0.0, h - contract) for h in weeks.values()), 2
        ),
        "nights": len(nights),
        "sleep_hours": _avg([n["asleep_min"] / 60 for n in nights]),
        "awakenings": _avg([n["awakenings"] for n in nights]),
        **{k: _avg([r["health"].get(k) for r in group]) for k in HEALTH},
    }


def _pairs(
    rows: list[dict[str, Any]], x: str, y: Any
) -> tuple[list[float], list[float]]:
    """(x, y) pairs where both are known."""
    both = [(r[x], y(r)) for r in rows if r[x] is not None and y(r) is not None]
    return [a for a, _ in both], [b for _, b in both]


def _in_band(
    row: dict[str, Any], low: float | None, high: float | None
) -> bool:
    """Whether a day falls in a band (None bounds: a day off)."""
    if low is None:
        return not row["worked"] and not row["absence"]
    return row["hours"] is not None and low <= row["hours"] < (high or 99)


def _key(day: date, unit: str) -> str:
    """The period a day belongs to."""
    if unit == "week":
        year, week, _ = day.isocalendar()
        return f"{year}-W{week:02d}"
    return f"{day:%Y-%m}" if unit == "month" else f"{day:%Y}"


def _avg(values: list[Any]) -> float | None:
    """Mean of the known values, rounded (None if none)."""
    known = [v for v in values if v is not None]
    return round(fmean(known), 2) if known else None
