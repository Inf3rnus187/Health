"""Make every page agree: one key per concept, daily values from raw data.

Run after each Apple import (and on demand from the web page):
0. stored data is aligned with the HealthKit catalog (French labels,
   domains, numeric category events, Health Auto Export percentages);
1. alias metrics are merged into their canonical metric (units
   converted), so e.g. SpO2 no longer lives under two keys;
2. every metric with raw samples gets its daily values recomputed with
   the single rule of :mod:`daily_rollup` — this also repairs days an
   interrupted import never wrote (e.g. weight present in the raw data
   but missing from the charts).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.services import canonical, catalog_sync, daily_rollup

_log = get_logger("reconcile")


async def run(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Merge aliases, then rebuild every sampled metric; report counts."""
    catalog = await _catalog(session, user_id)
    merged = await canonical.merge(session, user_id)
    await session.commit()
    tz = await daily_rollup.user_zone(session, user_id)
    days = 0
    metrics = await _sampled(session, user_id)
    for metric in metrics:
        days += await daily_rollup.rebuild(session, user_id, metric, tz)
        await session.commit()
    report = {
        "merged": merged,
        "metrics": len(metrics),
        "days": days,
        **catalog,
    }
    _log.info("reconciled", user_id=user_id, **report)
    return report


async def _catalog(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Align stored data with the HealthKit catalog (see catalog_sync)."""
    report = {
        "definitions": await catalog_sync.sync_definitions(session),
        "categories": await catalog_sync.backfill_categories(session, user_id),
        "percentages": await catalog_sync.tag_percentages(session, user_id),
    }
    await session.commit()
    return report


async def _sampled(
    session: AsyncSession, user_id: str
) -> list[MetricDefinition]:
    """Metrics for which the user has numeric raw samples."""
    ids = (
        select(HealthSample.metric_id)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.value_num.is_not(None),
        )
        .distinct()
    )
    result = await session.execute(
        select(MetricDefinition)
        .where(MetricDefinition.id.in_(ids))
        .order_by(MetricDefinition.key)
    )
    return list(result.scalars().all())
