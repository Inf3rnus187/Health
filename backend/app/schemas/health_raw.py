"""Schemas for browsing raw Apple Health data."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SampleOut(BaseModel):
    """One raw health sample."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    metric_id: str
    start_at: datetime
    end_at: datetime | None
    value_num: float | None
    value_text: str | None
    unit: str | None
    source: str


class SamplePage(BaseModel):
    """A page of raw samples plus the total match count."""

    items: list[SampleOut]
    total: int
    limit: int
    offset: int


class WorkoutOut(BaseModel):
    """One imported workout."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    activity_type: str
    start_at: datetime
    end_at: datetime | None
    duration_min: float | None
    energy_kcal: float | None
    distance_km: float | None


class EcgOut(BaseModel):
    """One ECG record (voltages stored on disk)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    recorded_at: datetime | None
    classification: str | None
    sample_rate_hz: float | None
    sample_count: int | None


class RouteOut(BaseModel):
    """One GPS route (GPX stored on disk)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    started_at: datetime | None
    point_count: int


class ObservationOut(BaseModel):
    """One clinical observation parsed from the CDA document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    value_num: float | None
    value_text: str | None
    unit: str | None
    effective_at: datetime | None


class ObservationPage(BaseModel):
    """A page of clinical observations plus the total match count."""

    items: list[ObservationOut]
    total: int
    limit: int
    offset: int


class ClinicalDocOut(BaseModel):
    """Summary of the stored CDA document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    observation_count: int
    created_at: datetime
