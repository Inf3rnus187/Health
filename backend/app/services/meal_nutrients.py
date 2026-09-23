"""A meal's estimated nutrients, written into Apple's nutrition metrics.

Each nutrient becomes one raw sample at the meal's time (source ``meal``,
tagged with the meal id), so the daily totals, charts, dashboards and
reports add them to any nutrition logged in Apple Health. Re-reading,
editing or deleting a meal replaces or removes exactly its samples.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid
from app.models.health_raw import HealthSample
from app.models.meal import Meal
from app.models.metric import MetricDefinition
from app.services import timed_entries
from app.services.apple_health.spec import synth_spec

_HK = "HKQuantityTypeIdentifier"
#: Analysis total → HealthKit type (same metric as Apple's nutrition).
NUTRIENTS = {
    "energy_kcal": f"{_HK}DietaryEnergyConsumed",
    "protein_g": f"{_HK}DietaryProtein",
    "carbs_g": f"{_HK}DietaryCarbohydrates",
    "sugars_g": f"{_HK}DietarySugar",
    "fat_g": f"{_HK}DietaryFatTotal",
    "sat_fat_g": f"{_HK}DietaryFatSaturated",
    "fiber_g": f"{_HK}DietaryFiber",
    "sodium_mg": f"{_HK}DietarySodium",
}
_SOURCE = "meal"


def tag(meal: Meal) -> str:
    """The marker linking samples to their meal."""
    return f"meal:{meal.id}"


async def record(
    session: AsyncSession, meal: Meal, totals: dict[str, float]
) -> None:
    """Replace the meal's nutrient samples with ``totals``."""
    await clear(session, meal)
    for name, hk_type in NUTRIENTS.items():
        value = totals.get(name)
        if not value or value <= 0:
            continue
        spec = synth_spec(hk_type, None)
        metric = await timed_entries.metric_for(session, spec)
        session.add(
            HealthSample(
                id=new_uuid(),
                user_id=meal.user_id,
                metric_id=metric.id,
                start_at=meal.eaten_at,
                value_num=round(value, 2),
                unit=spec.unit,
                source=_SOURCE,
                device=tag(meal),
            )
        )
        await timed_entries.refresh(
            session, meal.user_id, metric, {meal.date_key}
        )


async def clear(session: AsyncSession, meal: Meal) -> None:
    """Remove the meal's nutrient samples and fix the daily totals."""
    result = await session.execute(
        select(HealthSample).where(
            HealthSample.user_id == meal.user_id,
            HealthSample.device == tag(meal),
        )
    )
    touched: dict[str, set[Any]] = {}
    for sample in result.scalars().all():
        day = await timed_entries.local_day(
            session, meal.user_id, sample.start_at
        )
        touched.setdefault(sample.metric_id, set()).add(day)
        await session.delete(sample)
    for metric_id, days in touched.items():
        metric = await session.get(MetricDefinition, metric_id)
        if metric is not None:
            await timed_entries.refresh(session, meal.user_id, metric, days)
