"""The app's sleep samples, night by night, into the daily sleep values.

A night is what ends before 18:00 on its wake-up day (the cut of
:mod:`sleep_nights`, which reads the same raw samples for bedtime,
wake-up and awakenings). Its phases come from the Apple Watch, which
writes them (asleep = core + deep + REM + unspecified, awake); only a
night the watch did not record takes another recorder's (an app), the
one with the most sleep — never several added. Time in bed comes from
every device that writes it (the iPhone's bedtime), overlaps merged.
Each total becomes one sample at noon of the wake-up day, under the
``sleep.*`` metrics, so the daily values follow the one rule.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import (
    SLEEP_RAW,
    SLEEP_STAGE_MAP,
    MetricSpec,
)
from app.services.healthkit_common import SOURCE, Touched
from app.services.sleep_nights import is_watch

#: The ids of the nights' totals (``night:<key>:<day>``).
NIGHT = "night:"
_CUT = time(18)  # as sleep_nights: after 18:00, the next night
_NOON = time(12)
_ASLEEP = "sleep.asleep"
_BED = "sleep.time_in_bed"
_KEYS = (
    _ASLEEP, "sleep.core", "sleep.deep", "sleep.rem", "sleep.awake",
    _BED,
)  # fmt: skip
_SPECS = {k: MetricSpec(k, k, "sleep", "duration", "min", "avg") for k in _KEYS}

Minutes = dict[str, float]


async def recompute(
    session: AsyncSession, user_id: str, tz: ZoneInfo, touched: Touched
) -> None:
    """Each changed night's minutes per stage, from its best device."""
    cache = MetricCache()
    raw = await cache.id_for(session, SLEEP_RAW)
    for day in sorted({_wake_day(end, tz) for end in touched.nights}):
        device, minutes = _pick(await _night(session, user_id, raw, day, tz))
        noon = datetime.combine(day, _NOON, tzinfo=tz).astimezone(UTC)
        ids = [f"{NIGHT}{key}:{day.isoformat()}" for key in _KEYS]
        await session.execute(
            delete(HealthSample).where(
                HealthSample.user_id == user_id,
                HealthSample.external_id.in_(ids),
            )
        )
        for key in _KEYS:
            metric_id = await cache.id_for(session, _SPECS[key])
            touched.metric(metric_id, noon)
            if minutes.get(key):
                await session.execute(
                    insert(HealthSample),
                    [_row(user_id, metric_id, noon, key, day, minutes, device)],
                )


def _row(
    user_id: str,
    metric_id: str,
    noon: datetime,
    key: str,
    day: date,
    minutes: Minutes,
    device: str | None,
) -> dict[str, object]:
    """One stage's minutes for the night, as a sample."""
    return {
        "id": new_uuid(), "user_id": user_id, "metric_id": metric_id,
        "start_at": noon, "end_at": None,
        "value_num": round(minutes[key], 1), "value_text": None,
        "unit": "min", "source": SOURCE, "device": device,
        "external_id": f"{NIGHT}{key}:{day.isoformat()}",
        "created_at": utcnow(),
    }  # fmt: skip


async def _night(
    session: AsyncSession, user_id: str, raw: str, day: date, tz: ZoneInfo
) -> list[HealthSample]:
    """The app's sleep samples ending in the night before ``day``."""
    first = datetime.combine(day - timedelta(days=1), _CUT, tzinfo=tz)
    last = datetime.combine(day, _CUT, tzinfo=tz)
    found = await session.execute(
        select(HealthSample).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == raw,
            HealthSample.source == SOURCE,
            HealthSample.end_at >= first.astimezone(UTC),
            HealthSample.end_at < last.astimezone(UTC),
        )
    )
    return list(found.scalars())


def _pick(samples: list[HealthSample]) -> tuple[str | None, Minutes]:
    """The night's phases (the watch's) and its time in bed (merged)."""
    per: dict[str | None, Minutes] = {}
    beds: list[tuple[datetime, datetime]] = []
    for sample in samples:
        keys = SLEEP_STAGE_MAP.get(sample.value_text or "", ())
        span = (_utc(sample.start_at), _utc(sample.end_at or sample.start_at))
        if keys == (_BED,):
            beds.append(span)
            continue
        minutes = per.setdefault(sample.device, {})
        for key in keys:
            minutes[key] = minutes.get(key, 0.0) + _minutes(*span)
    device = _recorder(per)
    out = dict(per[device]) if device in per else {}
    in_bed = sum(_minutes(*span) for span in _merged(beds))
    if in_bed:
        out[_BED] = in_bed
    return device, out


def _recorder(per: dict[str | None, Minutes]) -> str | None:
    """The watch; without it, the recorder that saw the most sleep."""
    if not per:
        return None
    return max(per, key=lambda d: (is_watch(d), per[d].get(_ASLEEP, 0.0)))


def _merged(
    spans: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Overlapping intervals merged (iPhone and watch both « in bed »)."""
    out: list[tuple[datetime, datetime]] = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _minutes(start: datetime, end: datetime) -> float:
    """An interval's length in minutes."""
    return (end - start).total_seconds() / 60


def _wake_day(at: datetime, tz: ZoneInfo) -> date:
    """The wake-up day a sleep sample ending at ``at`` belongs to."""
    local = _utc(at).astimezone(tz)
    return local.date() + timedelta(days=1 if local.time() >= _CUT else 0)


def _utc(at: datetime) -> datetime:
    """A stored time as aware UTC (SQLite gives it back naive)."""
    return at if at.tzinfo else at.replace(tzinfo=UTC)
