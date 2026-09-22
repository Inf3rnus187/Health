"""Async photo pipeline: normalize → quality → rate → compare (§8).

Method v2 (see :mod:`photo_method`): deterministic quality control, a
blinded rating of the photo on anchored 0-10 scales, then counterbalanced
paired comparisons against the baseline and the ~7/30/90-day photos. The
long-term statistics are computed on read by :mod:`photo_trend`.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ollama
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.photo import Photo, PhotoAnalysis
from app.services import (
    imaging,
    photo_compare,
    photo_method,
    photo_quality,
    photo_storage,
)

_log = get_logger("photo")
_settings = get_settings()


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
    """Quality-check, rate and compare; the photo stays viewable anyway."""
    output: dict[str, Any] = {
        "method": photo_method.METHOD,
        "quality": photo_quality.assess(normalized),
    }
    if not output["quality"]["ok"]:
        _store(session, photo, output)
        photo.status = "low_quality"
        return
    try:
        output.update(await _rate(photo.angle, normalized))
    except Exception as exc:  # noqa: BLE001
        photo.status = "ai_failed"
        _log.warning("photo_ai_failed", photo_id=photo.id, error=str(exc))
        return
    output["comparisons"] = await _compare_all(session, photo, normalized)
    _store(session, photo, output)
    photo.status = "analyzed"


async def _rate(angle: str, image: bytes) -> dict[str, Any]:
    """Blinded 0-10 rating of one photo on the angle's anchored scales."""
    raw = await ollama.vision_json(photo_method.absolute_prompt(angle), image)
    scores = photo_method.read_scores(raw, angle)
    if not scores:
        raise ValueError(f"no usable score in the model answer: {raw}")
    return {
        "scores": scores,
        "labels": {c.key: c.label for c in photo_method.criteria_for(angle)},
        "confidence": _confidence(raw.get("confidence")),
        "pose_ok": raw.get("pose_ok") is not False,
        "remarks": str(raw.get("remarks") or "")[:300],
    }


async def _compare_all(
    session: AsyncSession, photo: Photo, image: bytes
) -> list[dict[str, Any]]:
    """Compare with each reference; a failed comparison is only skipped."""
    out: list[dict[str, Any]] = []
    for ref in await photo_compare.references(session, photo):
        try:
            result = await photo_compare.compare(photo.angle, ref.data, image)
        except Exception as exc:  # noqa: BLE001
            _log.warning("photo_compare_failed", error=str(exc))
            continue
        out.append(
            {
                "horizon": ref.horizon,
                "label": ref.label,
                "ref_photo_id": ref.photo.id,
                "ref_date": ref.photo.date_key.isoformat(),
                **result,
            }
        )
    return out


def _confidence(value: Any) -> float | None:
    """Model self-reported confidence, clamped to [0, 1]."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number)) if math.isfinite(number) else None


def _store(session: AsyncSession, photo: Photo, output: dict[str, Any]) -> None:
    """Persist a new versioned analysis row (history is never erased)."""
    comparisons = output.get("comparisons", [])
    baseline = next(
        (c["ref_photo_id"] for c in comparisons if c["horizon"] == "baseline"),
        None,
    )
    session.add(
        PhotoAnalysis(
            photo_id=photo.id,
            model=_settings.ollama_vision_model,
            prompt_version=photo_method.METHOD,
            raw_output=output,
            derived_metrics=output.get("scores"),
            comparison_ref=baseline,
        )
    )
