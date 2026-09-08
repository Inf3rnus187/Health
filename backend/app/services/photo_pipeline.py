"""Async photo pipeline: normalize → analyse (Ollama) → compare (§8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ollama
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.photo import Photo, PhotoAnalysis
from app.schemas.measurement import MeasurementIn
from app.services import imaging, photo_storage, photos
from app.services import measurements as measure

_log = get_logger("photo")
_settings = get_settings()

_PROMPT = (
    "You are a fitness progress analyst. Look at the silhouette in this "
    "photo and answer ONLY with a JSON object with keys: "
    '"silhouette_change" (short French text vs a leaner/heavier trend), '
    '"waist_estimate" (one of thin, medium, wide), '
    '"posture" (short French text). No prose outside the JSON.'
)


async def process(session: AsyncSession, photo_id: str) -> None:
    """Run the full pipeline for one photo, marking status/errors."""
    photo = await session.get(Photo, photo_id)
    if photo is None:
        return
    try:
        await _run(session, photo)
    except Exception as exc:  # noqa: BLE001
        photo.status = "error"
        _log.warning("photo_failed", photo_id=photo_id, error=str(exc))
    await session.commit()


async def _run(session: AsyncSession, photo: Photo) -> None:
    """Normalize, analyse and store results for ``photo``."""
    target = photo_storage.normalized_path(photo.user_id, photo.id, photo.angle)
    imaging.normalize(Path(photo.original_path), target)
    photo.normalized_path = str(target)
    photo.status = "normalized"
    result = await ollama.vision_json(_PROMPT, target.read_bytes())
    ref = await photos.latest_before(
        session, photo.user_id, photo.angle, photo.taken_at
    )
    _store(session, photo, result, ref.id if ref else None)
    await _inject(session, photo, result)
    photo.status = "analyzed"


def _store(
    session: AsyncSession,
    photo: Photo,
    result: dict[str, Any],
    comparison_ref: str | None,
) -> None:
    """Persist a versioned analysis row."""
    session.add(
        PhotoAnalysis(
            photo_id=photo.id,
            model=_settings.ollama_vision_model,
            prompt_version=_settings.photo_prompt_version,
            raw_output=result,
            derived_metrics=_derived(result),
            comparison_ref=comparison_ref,
        )
    )


def _derived(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the derived-metric subset from a raw analysis."""
    keys = ("silhouette_change", "waist_estimate", "posture")
    return {k: result[k] for k in keys if k in result}


async def _inject(
    session: AsyncSession, photo: Photo, result: dict[str, Any]
) -> None:
    """Inject the AI silhouette change as a measurement (source=ai)."""
    change = result.get("silhouette_change")
    if not isinstance(change, str) or not change:
        return
    item = MeasurementIn(
        metric_key="ai.silhouette_change",
        date_key=photo.date_key,
        value=change,
    )
    await measure.record_batch(session, photo.user_id, [item], source="ai")
