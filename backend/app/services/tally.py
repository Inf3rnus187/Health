"""Increment a daily counter (bouteille d'eau, café, cigarette, pipi).

The daily fact table keeps one row per metric/day, so a plain ingest
*replaces* the day's value — wrong for a one-tap counter. ``increment``
reads the current day total, adds the amount and upserts the sum, so each
tap (or an assistant's "add one") adds to the running total for the day.
A negative amount takes back a wrong entry; the total never goes below 0.
A pee (``elimination.urination``) is a timed journal entry: each one is
logged with its time, the day's value is their count. ``work.start`` /
``work.end`` clock in / out now (:mod:`work_tap`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError
from app.schemas.measurement import MeasurementIn
from app.services import audit, urination, work_tap
from app.services import measurement_values as values
from app.services import measurements as measure
from app.services import metrics as metrics_service
from app.services.canonical import canonical


@dataclass(frozen=True)
class Tally:
    """A counter's day total before and after one increment."""

    previous: float
    total: float
    #: A line for the Shortcut's notification (work taps).
    detail: str = ""


async def increment(
    session: AsyncSession,
    user_id: str,
    metric_key: str,
    amount: float,
    day: date,
    *,
    token_id: str | None = None,
) -> Tally:
    """Add ``amount`` to a metric's daily total; return both totals."""
    timed = await _timed(session, user_id, metric_key, amount, day)
    if timed is not None:
        await _log(session, user_id, metric_key, day, timed, token_id)
        return timed
    metric = await metrics_service.get_metric(session, metric_key)
    previous = await _current(session, user_id, metric_key, day)
    total = previous + amount
    if total < 0:
        raise InvalidInputError(
            f"{metric_key}: the total of {day} is {previous:g}, "
            "it cannot go below 0"
        )
    values.validate(metric, total)
    item = MeasurementIn(metric_key=metric_key, date_key=day, value=total)
    await measure.record_batch(
        session, user_id, [item], source="watch", token_id=token_id
    )
    step = Tally(previous=previous, total=total)
    await _log(session, user_id, metric_key, day, step, token_id)
    return step


async def _timed(
    session: AsyncSession,
    user_id: str,
    metric_key: str,
    amount: float,
    day: date,
) -> Tally | None:
    """A tap kept with its time (pee, clock in / out), else None."""
    if metric_key in work_tap.KINDS:
        before, after, line = await work_tap.tap(
            session, user_id, metric_key, amount, day
        )
        return Tally(previous=before, total=after, detail=line)
    if canonical(metric_key) == urination.SPEC.key:
        count = await urination.tap(session, user_id, amount, day)
        return Tally(previous=count[0], total=count[1])
    return None


async def _log(
    session: AsyncSession,
    user_id: str,
    metric_key: str,
    day: date,
    step: Tally,
    token_id: str | None,
) -> None:
    """Audit one step with the day's total before and after it."""
    await audit.record(
        session,
        action="add",
        entity="measurement",
        user_id=user_id,
        source="token" if token_id else "api",
        payload={
            "metric": metric_key,
            "date": day.isoformat(),
            "previous": step.previous,
            "total": step.total,
        },
    )


async def _current(
    session: AsyncSession, user_id: str, metric_key: str, day: date
) -> float:
    """Return the metric's stored value for the day, or 0."""
    rows = await measure.query(
        session, user_id, metric_key=metric_key, start=day, end=day
    )
    for row in rows:
        if row.event_id is None and row.value_num is not None:
            return row.value_num
    return 0.0
