"""AI reading of a meal: photo → foods, foods → checked nutrients.

1. With a photo, the vision model (e.g. MedGemma 1.5) lists the foods and
   estimates the portions; the user's description takes precedence.
2. The text model (e.g. MedGemma 27B) estimates each food's nutrients
   (Ciqual reference values) and judges the meal for the user's declared
   conditions (score 0-10, verdict, positives, points to watch).
3. :mod:`meal_nutrition` keeps only plausible foods and recomputes the
   energy; the totals feed Apple's nutrition metrics (:mod:`meal_nutrients`).

States: queued → running → done | failed (with the error), a time limit,
and readings a worker restart interrupted are re-queued.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ollama
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.meal import Meal
from app.services import (
    conditions,
    meal_foods,
    meal_nutrients,
    meal_nutrition,
    meal_photo,
    meal_prompt,
    meals,
)
from app.services.daily_rollup import user_zone
from app.services.timed_entries import utc
from app.workers.queue import enqueue, enqueue_many

_log = get_logger("meal_ai")
_TIME_LIMIT = 900.0
_TOKENS = 1500
PENDING = ("queued", "running")


async def queue(session: AsyncSession, meal: Meal) -> bool:
    """Mark a meal for (re-)reading and hand it to the worker."""
    meal.analysis_status = "queued"
    await session.commit()
    if await enqueue("analyze_meal", meal.id):
        return True
    meal.analysis_status = None
    await session.commit()
    return False


async def run(session: AsyncSession, meal_id: str) -> None:
    """Worker entry point: read one meal, record the outcome."""
    meal = await session.get(Meal, meal_id)
    if meal is None:
        return
    meal.analysis_status = "running"
    await session.commit()
    try:
        result = await asyncio.wait_for(analyze(session, meal), _TIME_LIMIT)
    except Exception as exc:  # noqa: BLE001 - reported on the meal
        await _fail(session, meal_id, exc)
        return
    meal.analysis, meal.analysis_status = result, "done"
    await session.commit()


async def analyze(session: AsyncSession, meal: Meal) -> dict[str, Any]:
    """Foods, checked nutrients and assessment of one meal."""
    seen, labels = await _look(meal)
    portions = await meal_foods.of_meal(session, meal)
    context = await _context(session, meal, seen)
    context["foods"] = meal_foods.context(portions)
    context["labels"] = labels
    answer = await ollama.text_json(
        meal_prompt.nutrition(context), max_tokens=_TOKENS
    )
    items, rejected = meal_nutrition.check(answer.get("items"))
    items = meal_foods.apply(items, portions)
    totals = meal_nutrition.totals(items)
    await meal_nutrients.record(session, meal, totals)
    return {
        "model": ollama.text_model(),
        "vision_model": get_settings().ollama_vision_model if seen else None,
        "seen": seen,
        "labels": labels,
        "foods": [food.name for food, _ in portions],
        "items": items,
        "rejected": rejected,
        "totals": totals,
        **meal_nutrition.assessment(answer),
        "finished_at": utcnow().isoformat(),
    }


async def requeue_stale(session: AsyncSession) -> int:
    """Re-queue readings a worker restart left queued / running."""
    result = await session.execute(
        select(Meal.id).where(Meal.analysis_status.in_(PENDING))
    )
    ids = [(meal_id,) for meal_id in result.scalars().all()]
    return await enqueue_many("analyze_meal", ids) if ids else 0


async def _context(
    session: AsyncSession, meal: Meal, seen: list[dict[str, Any]]
) -> dict[str, Any]:
    """What the text model is told: meal, time, text, photo, conditions."""
    current = await conditions.list_all(session, meal.user_id)
    tz = await user_zone(session, meal.user_id)
    return {
        "meal": meals.TYPES.get(meal.meal_type, meal.meal_type).lower(),
        "time": utc(meal.eaten_at).astimezone(tz).strftime("%H:%M"),
        "description": meal.description,
        "seen": seen,
        "conditions": [c.name for c in current if c.status != "resolved"],
    }


async def _look(
    meal: Meal,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """What the vision model sees: foods and portions, and labels.

    The labels are read on the other photos (a pack, a nutrition table);
    nothing without a photo.
    """
    photos = meal_photo.read_all(meal)
    if not photos:
        return [], []
    prompt = meal_prompt.look(meal.description, len(photos))
    answer = await ollama.vision_json(
        prompt, photos[0] if len(photos) == 1 else photos
    )
    return _dicts(answer.get("items"), 30), _dicts(answer.get("labels"), 10)


def _dicts(found: Any, most: int) -> list[dict[str, Any]]:
    """The dict entries of a list the model returned (at most ``most``)."""
    if not isinstance(found, list):
        return []
    return [item for item in found if isinstance(item, dict)][:most]


async def _fail(session: AsyncSession, meal_id: str, exc: Exception) -> None:
    """Record a failed reading (the error is shown on the meal)."""
    reason = "délai dépassé" if isinstance(exc, TimeoutError) else str(exc)
    _log.warning("meal_analysis_failed", meal=meal_id, error=reason)
    await session.rollback()
    meal = await session.get(Meal, meal_id)
    if meal is not None:
        meal.analysis_status = "failed"
        meal.analysis = {"error": reason[:300] or type(exc).__name__}
        await session.commit()
