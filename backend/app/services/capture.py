"""Mode B capture session: open event, pre-fill night data (§7.2)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utcnow
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.schemas.capture import CaptureRequest, CaptureResponse
from app.schemas.event import EventCreate
from app.schemas.measurement import MeasurementIn, MeasurementOut
from app.schemas.metric import MetricOut
from app.services import events
from app.services import measurements as measure

_PREFILL_SOURCES = ("watch", "ppc")


async def capture(
    session: AsyncSession,
    user_id: str,
    data: CaptureRequest,
    *,
    source: str,
    token_id: str | None = None,
) -> CaptureResponse:
    """Open a capture session, record inputs, return the day's form."""
    event = await events.create_event(
        session, user_id, EventCreate(type="capture_session")
    )
    items = _capture_items(data)
    await measure.record_batch(
        session, user_id, items, source=source, token_id=token_id
    )
    return CaptureResponse(
        event_id=event.id,
        prefilled=await _prefill(session, user_id),
        complement=await _complement(session),
    )


def _capture_items(data: CaptureRequest) -> list[MeasurementIn]:
    """Build the daily measurements captured in mode B."""
    day = data.date_key or utcnow().date()
    items = [
        MeasurementIn(
            metric_key="photo.face_done", date_key=day, value=data.photo_face
        ),
        MeasurementIn(
            metric_key="photo.profil_done",
            date_key=day,
            value=data.photo_profil,
        ),
    ]
    if data.weight is not None:
        items.append(
            MeasurementIn(
                metric_key="body.weight", date_key=day, value=data.weight
            )
        )
    return items


async def _prefill(session: AsyncSession, user_id: str) -> list[MeasurementOut]:
    """Return the most recent Watch/CPAP measurements to pre-fill."""
    metric_ids = select(MetricDefinition.id).where(
        MetricDefinition.source.in_(_PREFILL_SOURCES)
    )
    stmt = (
        select(Measurement)
        .where(
            Measurement.user_id == user_id,
            Measurement.metric_id.in_(metric_ids),
        )
        .order_by(Measurement.date_key.desc(), Measurement.recorded_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [MeasurementOut.model_validate(row) for row in rows]


async def _complement(
    session: AsyncSession,
) -> list[MetricOut]:
    """Return the active manual metrics to complete by hand."""
    result = await session.execute(
        select(MetricDefinition)
        .where(
            MetricDefinition.source == "manual",
            MetricDefinition.is_active.is_(True),
        )
        .order_by(MetricDefinition.key)
    )
    metrics = result.scalars().all()
    return [MetricOut.model_validate(metric) for metric in metrics]
