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
    """Store the normalized image, then analyse it (failures isolated)."""
    photo = await session.get(Photo, photo_id)
    if photo is None:
        return
    normalized = await _normalize(session, photo)
    if normalized is not None:
        await _analyse(session, photo, normalized)
    await session.commit()


async def _normalize(session: AsyncSession, photo: Photo) -> bytes | None:
    """Decode/orient/store the image; ``error`` status only if this fails."""
    try:
        target = photo_storage.normalized_path(
            photo.user_id, photo.id, photo.angle
        )
        original = photo_storage.read_bytes(Path(photo.original_path))
        normalized = imaging.normalize_bytes(original)
        photo_storage.write_bytes(target, normalized)
        photo.normalized_path = str(target)
        photo.status = "normalized"
        return normalized
    except Exception as exc:  # noqa: BLE001
        photo.status = "error"
        _log.warning(
            "photo_normalize_failed", photo_id=photo.id, error=str(exc)
        )
        return None


async def _analyse(
    session: AsyncSession, photo: Photo, normalized: bytes
) -> None:
    """Run the AI analysis; the photo stays viewable if the AI is down."""
    try:
        result = await ollama.vision_json(_PROMPT, normalized)
        ref = await photos.latest_before(
            session, photo.user_id, photo.angle, photo.taken_at
        )
        _store(session, photo, result, ref.id if ref else None)
        await _inject(session, photo, result)
        photo.status = "analyzed"
    except Exception as exc:  # noqa: BLE001
        photo.status = "ai_failed"
        _log.warning("photo_ai_failed", photo_id=photo.id, error=str(exc))


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
