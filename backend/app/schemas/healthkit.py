"""What the iPhone app sends to ``POST /sync/healthkit``, and the answer.

Dates are ISO 8601 (``2026-09-26T08:00:00+02:00``); a date without an
offset is the user's local time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HkSample(BaseModel):
    """One HealthKit sample (quantity or category), known by its UUID."""

    uuid: str = Field(min_length=1, max_length=64)
    #: ``HKQuantityTypeIdentifier…`` or ``HKCategoryTypeIdentifier…``.
    type: str = Field(min_length=1, max_length=120)
    start: datetime
    end: datetime | None = None
    #: A number in ``unit`` (a quantity: HealthKit's own value, 0.97 for
    #: 97 %); a category: its ``HKCategoryValue…`` name, or for sleep the
    #: HKCategoryValueSleepAnalysis number (0 in bed … 5 REM).
    value: float | str | None = None
    unit: str | None = Field(default=None, max_length=32)
    #: The device that measured it (« Apple Watch de Test »).
    device: str | None = Field(default=None, max_length=128)


class HkStatistic(BaseModel):
    """A cumulative type's total over an interval, as HealthKit adds it up.

    ``HKStatisticsCollectionQuery`` with ``.cumulativeSum``: the iPhone
    and the watch counted once.
    """

    type: str = Field(min_length=1, max_length=120)
    start: datetime
    end: datetime
    sum: float
    unit: str | None = Field(default=None, max_length=32)


class HkWorkout(BaseModel):
    """One workout, known by its UUID."""

    uuid: str = Field(min_length=1, max_length=64)
    #: ``HKWorkoutActivityTypeWalking`` (or ``walking``).
    activity: str = Field(min_length=1, max_length=80)
    start: datetime
    end: datetime
    duration_min: float | None = Field(default=None, ge=0)
    energy_kcal: float | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)


class HealthKitSync(BaseModel):
    """One sync: new samples, sums, workouts and what was deleted."""

    samples: list[HkSample] = Field(default_factory=list, max_length=5000)
    statistics: list[HkStatistic] = Field(default_factory=list, max_length=5000)
    workouts: list[HkWorkout] = Field(default_factory=list, max_length=500)
    #: UUIDs of samples or workouts deleted in the Health app.
    deleted: list[str] = Field(default_factory=list, max_length=5000)


class HealthKitResult(BaseModel):
    """What a sync stored, removed and recomputed, and what it refused."""

    samples: int
    statistics: int
    workouts: int
    deleted: int
    #: Daily values recomputed (all metrics together).
    days: int
    #: ``{"type", "reason", "count"}`` for each kind of line refused.
    skipped: list[dict[str, Any]]


class HealthKitStatus(BaseModel):
    """What the hub holds from the app."""

    last_sync_at: datetime | None
    samples: int
    workouts: int
    #: Per metric: ``key``, ``label``, ``samples``, ``last`` (newest start).
    metrics: list[dict[str, Any]]
