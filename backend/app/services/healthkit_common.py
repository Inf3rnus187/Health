"""Shared pieces of the iPhone app sync (:mod:`healthkit_sync`)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypeVar
from zoneinfo import ZoneInfo

#: The channel the app's data is stored under (one HealthKit channel per
#: day, like the native export and Health Auto Export: never added up).
SOURCE = "healthkit"
QUANTITY = "HKQuantityTypeIdentifier"
CATEGORY = "HKCategoryTypeIdentifier"
_CHUNK = 500  # ids per IN (…): SQLite limits bound parameters

T = TypeVar("T")


@dataclass
class Touched:
    """What a sync changed, so that only those days are recomputed."""

    #: metric id → instants whose local day changed.
    metrics: dict[str, list[datetime]] = field(default_factory=dict)
    #: Ends of sleep samples (their nights change).
    nights: list[datetime] = field(default_factory=list)
    #: Starts of workouts (their days change).
    workouts: list[datetime] = field(default_factory=list)
    #: (type, reason) → lines refused.
    skipped: Counter[tuple[str, str]] = field(default_factory=Counter)

    def metric(self, metric_id: str, at: datetime) -> None:
        """Mark a metric's day as changed."""
        self.metrics.setdefault(metric_id, []).append(at)

    def skip(self, kind: str, reason: str) -> None:
        """Count a refused line."""
        self.skipped[(kind, reason)] += 1


def aware(value: datetime, tz: ZoneInfo) -> datetime:
    """The instant in UTC; a time sent without offset is local."""
    local = value if value.tzinfo else value.replace(tzinfo=tz)
    return local.astimezone(UTC)


def chunks(items: list[T]) -> Iterator[list[T]]:
    """``items`` in slices small enough for one statement."""
    for start in range(0, len(items), _CHUNK):
        yield items[start : start + _CHUNK]
