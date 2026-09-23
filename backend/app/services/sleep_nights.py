"""Nights of sleep read from the raw sleep samples (Apple Watch…).

A night belongs to the day you wake up (like the daily sleep values):
the samples ending between 18:00 the evening before and 18:00 that day.
When several devices recorded the same night, the one that saw the most
sleep is kept (no double counting). Per night:

* asleep minutes, awake minutes inside the night;
* awakenings — the awake phases between falling asleep and waking up
  (without phases, the breaks of 5 minutes or more);
* blocks — sleep "in several goes": stretches split by 60 minutes or
  more without sleep; the longest block;
* bedtime (first sleep) and wake-up (last sleep), local time.

A night without raw samples falls back on the daily ``sleep.asleep``
value (Health Auto Export): minutes only. A night typed by hand (watch
out of battery) is a sample from the source ``manual``.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.services import measurements, timed_entries
from app.services.apple_health.spec import SLEEP_RAW
from app.services.timed_entries import utc

#: A night runs from 18:00 the day before to 18:00 the wake-up day.
_CUT = time(18, 0)
_AWAKENING = timedelta(minutes=5)
_BLOCK_GAP = timedelta(minutes=60)

Interval = tuple[datetime, datetime]


class Night(NamedTuple):
    """One night of sleep (``wake_day`` = the day you woke up)."""

    wake_day: date
    asleep_min: float
    awake_min: float | None
    awakenings: int | None
    blocks: int | None
    longest_block_min: float | None
    bedtime: datetime | None
    wake_time: datetime | None
    source: str


async def nights(
    session: AsyncSession,
    user_id: str,
    first: date,
    last: date,
    tz: ZoneInfo,
) -> dict[date, Night]:
    """The nights whose wake-up day is in ``first``..``last``."""
    metric = await timed_entries.metric_for(session, SLEEP_RAW)
    start = utc(datetime.combine(first - timedelta(days=1), _CUT, tzinfo=tz))
    end = utc(datetime.combine(last, _CUT, tzinfo=tz))
    rows = await session.execute(
        select(HealthSample).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric.id,
            HealthSample.end_at >= start,
            HealthSample.end_at < end,
        )
    )
    groups: dict[tuple[date, str], list[HealthSample]] = defaultdict(list)
    for row in rows.scalars():
        groups[(_wake_day(row, tz), _origin(row))].append(row)
    found: dict[date, Night] = {}
    for (day, origin), samples in groups.items():
        night = read_night(day, samples, origin, tz)
        best = found.get(day)
        if night and (best is None or night.asleep_min > best.asleep_min):
            found[day] = night
    await _daily_only(session, user_id, first, last, found)
    return dict(sorted(found.items()))


async def first_day(
    session: AsyncSession, user_id: str, tz: ZoneInfo
) -> date | None:
    """The wake-up day of the first night known (samples or daily)."""
    metric = await timed_entries.metric_for(session, SLEEP_RAW)
    raw = await session.execute(
        select(func.min(HealthSample.end_at)).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric.id,
        )
    )
    first = raw.scalar_one_or_none()
    days = [utc(first).astimezone(tz).date()] if first else []
    daily = await measurements.query(
        session, user_id, metric_key="sleep.asleep"
    )
    days += [row.date_key for row in daily[:1]]
    return min(days) if days else None


def read_night(
    day: date, samples: list[HealthSample], origin: str, tz: ZoneInfo
) -> Night | None:
    """One device's night from its samples (None without sleep)."""
    asleep = _merge([_span(s) for s in samples if _stage(s) == "asleep"])
    if not asleep:
        return None
    awake = [_span(s) for s in samples if _stage(s) == "awake"]
    inside = [a for a in awake if asleep[0][0] <= a[0] < asleep[-1][1]]
    blocks = _blocks(asleep)
    return Night(
        wake_day=day,
        asleep_min=round(sum(_minutes(i) for i in asleep), 1),
        awake_min=round(sum(_minutes(i) for i in inside), 1),
        awakenings=_awakenings(samples, asleep, inside, bool(awake)),
        blocks=len(blocks),
        longest_block_min=round(max(_minutes(b) for b in blocks), 1),
        bedtime=asleep[0][0].astimezone(tz),
        wake_time=asleep[-1][1].astimezone(tz),
        source=origin,
    )


def as_dict(night: Night) -> dict[str, Any]:
    """A night for the API (times as ``HH:MM``)."""
    out = night._asdict()
    for key in ("bedtime", "wake_time"):
        value = out[key]
        out[key] = f"{value:%H:%M}" if value else None
    return out


def _awakenings(
    samples: list[HealthSample],
    asleep: list[Interval],
    inside: list[Interval],
    has_phases: bool,
) -> int:
    """Awake phases in the night; typed by hand; or breaks of 5 min+."""
    typed = [s.value_num for s in samples if s.source == "manual"]
    if typed and typed[0] is not None:
        return int(typed[0])
    if has_phases:
        return len(inside)
    gaps = [b[0] - a[1] for a, b in zip(asleep, asleep[1:], strict=False)]
    return sum(gap >= _AWAKENING for gap in gaps)


async def _daily_only(
    session: AsyncSession,
    user_id: str,
    first: date,
    last: date,
    found: dict[date, Night],
) -> None:
    """Nights known only by the daily ``sleep.asleep`` value (minutes)."""
    rows = await measurements.query(
        session, user_id, metric_key="sleep.asleep", start=first, end=last
    )
    for row in rows:
        if row.date_key not in found and row.value_num:
            found[row.date_key] = Night(
                row.date_key, row.value_num, None, None, None, None, None,
                None, f"{row.source}:jour",
            )  # fmt: skip


def _stage(row: HealthSample) -> str:
    """asleep, awake or inbed from the category value."""
    value = (row.value_text or "").lower()
    if "awake" in value:
        return "awake"
    if "inbed" in value:
        return "inbed"
    return (
        "asleep"
        if "asleep" in value or value in {"core", "deep", "rem"}
        else ""
    )


def _span(row: HealthSample) -> Interval:
    """A sample as an aware UTC interval."""
    start = utc(row.start_at)
    return start, utc(row.end_at) if row.end_at else start


def _merge(spans: list[Interval]) -> list[Interval]:
    """Overlapping intervals merged, in order."""
    merged: list[Interval] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _blocks(asleep: list[Interval]) -> list[Interval]:
    """Sleep stretches split by an hour or more without sleep."""
    blocks = [asleep[0]]
    for start, end in asleep[1:]:
        if start - blocks[-1][1] >= _BLOCK_GAP:
            blocks.append((start, end))
        else:
            blocks[-1] = (blocks[-1][0], end)
    return blocks


def _minutes(span: Interval) -> float:
    """An interval's length in minutes."""
    return (span[1] - span[0]).total_seconds() / 60


def _wake_day(row: HealthSample, tz: ZoneInfo) -> date:
    """The wake-up day a sample belongs to (18:00 cut)."""
    local = utc(row.end_at or row.start_at).astimezone(tz)
    return local.date() + timedelta(days=1 if local.time() >= _CUT else 0)


def _origin(row: HealthSample) -> str:
    """Who recorded a sample (source and device)."""
    return f"{row.source}:{row.device or ''}"
