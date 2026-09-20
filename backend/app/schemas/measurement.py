"""Measurement I/O schemas (batch write + typed read)."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


class MeasurementIn(BaseModel):
    """One value to record for a metric on a given day."""

    metric_key: str
    date_key: date
    value: Any
    recorded_at: datetime | None = None
    event_id: str | None = None
    source: str | None = None


class MeasurementBatch(BaseModel):
    """A batch of measurements (idempotent by date+metric[+event])."""

    items: list[MeasurementIn] = Field(min_length=1, max_length=500)


class MeasurementOut(BaseModel):
    """Stored measurement plus a convenience ``value`` field."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    metric_id: str
    event_id: str | None
    date_key: date
    recorded_at: datetime
    source: str
    value_num: float | None
    value_bool: bool | None
    value_text: str | None
    value_time: time | None
    value_json: dict[str, Any] | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def value(self) -> Any:
        """Return whichever typed column holds this value."""
        columns = (
            self.value_num,
            self.value_bool,
            self.value_text,
            self.value_time,
            self.value_json,
        )
        for candidate in columns:
            if candidate is not None:
                return candidate
        return None


class IdList(BaseModel):
    """A list of measurement ids to delete in bulk."""

    ids: list[str] = Field(min_length=1, max_length=1000)


class DeleteResult(BaseModel):
    """How many rows a bulk delete removed."""

    deleted: int


class SeriesPoint(BaseModel):
    """One point of an aggregated time series."""

    date_key: date
    value: float


class Series(BaseModel):
    """A rolling-aggregated series ready to plot."""

    metric_key: str
    agg: str
    window_days: int
    points: list[SeriesPoint]


class TrendOut(BaseModel):
    """A calendar-bucketed series (day/week/month/year)."""

    metric_key: str
    bucket: str
    points: list[SeriesPoint]
