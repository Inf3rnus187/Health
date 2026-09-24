"""The patient's facts, numbered, for the AI clinical synthesis.

Everything the hub knows, as short dated French lines: declared
conditions and treatments, markers with their bands, lab / FibroScan
results with their previous value, weight trend, key Apple Health
indicators (last 30 days vs the 30 before and a year ago), the photo
trend and the documents. The synthesis may only use and cite these.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    conditions,
    fact_doses,
    fact_record,
    fact_trends,
    fact_values,
    medical,
    metabolic,
    photo_trend,
    record_results,
    treatments,
    weight_trend,
)


class Fact(NamedTuple):
    """One numbered fact (``F12``) of a section."""

    id: str
    section: str
    text: str


async def gather(session: AsyncSession, user_id: str) -> list[Fact]:
    """Every fact about the user, numbered in reading order."""
    docs = await medical.list_documents(session, user_id)
    origin = record_results.origins(docs)
    markers = await metabolic.markers(session, user_id)
    weights = await weight_trend.series(session, user_id)
    results = await record_results.results(session, user_id, origin)
    lines = fact_record.profile(markers["profile"])
    lines += fact_record.conditions(await conditions.list_all(session, user_id))
    lines += fact_record.treatments(await treatments.list_all(session, user_id))
    lines += await fact_doses.adherence(session, user_id)
    lines += fact_values.markers(markers["markers"])
    lines += fact_values.results(results)
    lines += fact_values.weight(weight_trend.summary(weights))
    lines += await fact_trends.indicators(session, user_id)
    lines += fact_trends.photos(await photo_trend.trend(session, user_id))
    lines += fact_record.documents(docs)
    return [Fact(f"F{i}", s, t) for i, (s, t) in enumerate(lines, 1)]


def as_json(facts: list[Fact]) -> list[dict[str, Any]]:
    """Facts as stored with the report."""
    return [fact._asdict() for fact in facts]
