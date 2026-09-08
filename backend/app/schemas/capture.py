"""Mode B (capture session) request/response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.schemas.measurement import MeasurementOut
from app.schemas.metric import MetricOut


class CaptureRequest(BaseModel):
    """Payload for a capture session (weight + photo flags)."""

    date_key: date | None = None
    weight: float | None = None
    photo_face: bool = False
    photo_profil: bool = False


class CaptureResponse(BaseModel):
    """Opened event, pre-filled night data and the manual form."""

    event_id: str
    prefilled: list[MeasurementOut]
    complement: list[MetricOut]
