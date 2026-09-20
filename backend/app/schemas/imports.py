"""Schemas for Apple Health import jobs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobOut(BaseModel):
    """Status and counts for one background import."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    phase: str
    processed: int
    samples: int
    workouts: int
    ecg: int
    routes: int
    error: str | None
    created_at: datetime
    updated_at: datetime | None
