"""What was spent on meals paid for: deliveries (Uber Eats…), meals bought.

From the traces with an amount of a period (``livraison``: the Uber Eats
orders and other deliveries; ``repas``: receipts, restaurants):

* total, orders, average basket, the largest order, the monthly average;
* per day, week or month — empty periods included, for a continuous
  chart (``auto``: days up to 2 months, weeks up to 13 months, months);
* per hour of the day, local time, and the late orders (21:00 – 05:00);
* the establishments that cost the most.

A proof, not a health meal: the Journal's meals are never counted here.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Evidence
from app.services.daily_rollup import user_zone
from app.services.timed_entries import day_bounds, utc

#: What « kind » selects.
KINDS: dict[str, tuple[str, ...]] = {
    "livraison": ("livraison",),
    "repas": ("repas",),
    "tout": ("livraison", "repas"),
}
LATE_FROM, LATE_UNTIL = 21, 5
TOP = 10
_DAYS_MAX, _WEEKS_MAX = 62, 400


class Order(NamedTuple):
    """One meal paid for, at its local time."""

    at: datetime
    amount: float
    name: str


async def meals(
    session: AsyncSession,
    user_id: str,
    span: tuple[date | None, date],
    kind: str,
    bucket: str,
) -> dict[str, Any]:
    """The spending of ``span`` (no start: from the first order)."""
    orders = await _orders(session, user_id, span, KINDS[kind])
    first = span[0] or (orders[0].at.date() if orders else span[1])
    last = span[1]
    step = _bucket(bucket, (last - first).days + 1)
    return {
        "start": first.isoformat(),
        "end": last.isoformat(),
        "bucket": step,
        **_totals(orders, (last - first).days + 1),
        "periods": _periods(orders, (first, last), step),
        "hours": _hours(orders),
        "vendors": _vendors(orders),
    }


async def _orders(
    session: AsyncSession,
    user_id: str,
    span: tuple[date | None, date],
    kinds: tuple[str, ...],
) -> list[Order]:
    """The traces with an amount, oldest first, at local time."""
    tz = await user_zone(session, user_id)
    stmt = select(Evidence.occurred_at, Evidence.amount, Evidence.title).where(
        Evidence.user_id == user_id,
        Evidence.kind.in_(kinds),
        Evidence.amount.is_not(None),
        Evidence.occurred_at < day_bounds(span[1], tz)[1],
    )
    if span[0] is not None:
        stmt = stmt.where(Evidence.occurred_at >= day_bounds(span[0], tz)[0])
    rows = await session.execute(stmt.order_by(Evidence.occurred_at))
    return [
        Order(_local(at, tz), float(amount), (title or "?").strip())
        for at, amount, title in rows
    ]


def _local(at: datetime, tz: ZoneInfo) -> datetime:
    """A stored instant (naive = UTC, SQLite) in local time."""
    return utc(at).astimezone(tz)


def _totals(orders: list[Order], days: int) -> dict[str, Any]:
    """Total, count, average, largest, monthly average, late orders."""
    total = round(sum(o.amount for o in orders), 2)
    late = [o for o in orders if _late(o.at.hour)]
    big = max(orders, key=lambda o: o.amount, default=None)
    return {
        "total": total,
        "count": len(orders),
        "average": round(total / len(orders), 2) if orders else None,
        "per_month": round(total * 30.44 / days, 2) if days else None,
        "largest": _order(big) if big else None,
        "late": {
            "count": len(late),
            "total": round(sum(o.amount for o in late), 2),
        },
    }


def _late(hour: int) -> bool:
    """Ordered from 21:00 to 04:59."""
    return hour >= LATE_FROM or hour < LATE_UNTIL


def _order(order: Order) -> dict[str, Any]:
    """The largest order, for the page."""
    return {
        "amount": order.amount,
        "name": order.name,
        "at": order.at.isoformat(timespec="minutes"),
    }


def _bucket(asked: str, days: int) -> str:
    """The period of the chart's bars (``auto``: from the span's length)."""
    if asked != "auto":
        return asked
    if days <= _DAYS_MAX:
        return "day"
    return "week" if days <= _WEEKS_MAX else "month"


def _start(day: date, step: str) -> date:
    """The first day of ``day``'s period."""
    if step == "week":
        return day - timedelta(days=day.weekday())
    if step == "month":
        return day.replace(day=1)
    return day


def _next(day: date, step: str) -> date:
    """The first day of the next period."""
    if step == "month":
        return (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return day + timedelta(days=7 if step == "week" else 1)


def _periods(
    orders: list[Order], span: tuple[date, date], step: str
) -> list[dict[str, Any]]:
    """Every period of the span, with what was spent (0 when nothing)."""
    sums: dict[date, list[float]] = defaultdict(list)
    for order in orders:
        sums[_start(order.at.date(), step)].append(order.amount)
    out = []
    day = _start(span[0], step)
    while day <= span[1]:
        spent = sums.get(day, [])
        out.append(
            {
                "start": day.isoformat(),
                "total": round(sum(spent), 2),
                "count": len(spent),
            }
        )
        day = _next(day, step)
    return out


def _hours(orders: list[Order]) -> list[dict[str, Any]]:
    """The 24 hours of the day: orders and amount, late ones flagged."""
    count = [0] * 24
    total = [0.0] * 24
    for order in orders:
        count[order.at.hour] += 1
        total[order.at.hour] += order.amount
    return [
        {
            "hour": h,
            "count": count[h],
            "total": round(total[h], 2),
            "late": _late(h),
        }
        for h in range(24)
    ]


def _vendors(orders: list[Order]) -> list[dict[str, Any]]:
    """The establishments that cost the most, with their share."""
    spent: dict[str, list[float]] = defaultdict(list)
    for order in orders:
        spent[order.name].append(order.amount)
    whole = sum(o.amount for o in orders) or 1.0
    ranked = sorted(spent.items(), key=lambda kv: -sum(kv[1]))[:TOP]
    return [
        {
            "name": name,
            "count": len(amounts),
            "total": round(sum(amounts), 2),
            "share": round(sum(amounts) / whole * 100, 1),
        }
        for name, amounts in ranked
    ]
