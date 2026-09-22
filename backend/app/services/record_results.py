"""Lab and imaging results of the record, with their source document.

Every ``bio.*`` / ``liver.*`` metric with its latest and previous value
and the document it came from.

The values are the ones every other page reads (same metrics), so the
Dossier, the markers, the charts and the reports agree.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.medical import MedicalDocument
from app.models.metric import MetricDefinition
from app.services.record_suggest import doc_ref

_PREFIXES = ("bio.", "liver.")
Origin = dict[tuple[str, str], dict[str, Any]]


def origins(docs: list[MedicalDocument]) -> Origin:
    """(metric key, ISO date) → the document the value was read from."""
    out: Origin = {}
    for doc in docs:
        for value in (doc.analysis or {}).get("values") or []:
            out.setdefault((value["key"], value["date"]), doc_ref(doc))
    return out


async def results(
    session: AsyncSession, user_id: str, origin: Origin
) -> list[dict[str, Any]]:
    """One entry per result metric, most recently measured first."""
    rows = await session.execute(
        select(
            MetricDefinition.key,
            MetricDefinition.label,
            MetricDefinition.unit,
            Measurement.date_key,
            Measurement.value_num,
            Measurement.source,
        )
        .join(Measurement, Measurement.metric_id == MetricDefinition.id)
        .where(
            Measurement.user_id == user_id,
            Measurement.value_num.is_not(None),
            or_(*(MetricDefinition.key.like(f"{p}%") for p in _PREFIXES)),
        )
        .order_by(MetricDefinition.key, Measurement.date_key)
    )
    grouped: dict[str, list[Any]] = {}
    for row in rows.all():
        grouped.setdefault(row.key, []).append(row)
    out = [_entry(history, origin) for history in grouped.values()]
    return sorted(
        out, key=lambda e: (e["latest"]["date"], e["key"]), reverse=True
    )


def _entry(history: list[Any], origin: Origin) -> dict[str, Any]:
    """Latest / previous value, change and provenance of one metric."""
    last = history[-1]
    prev = history[-2] if len(history) > 1 else None
    return {
        "key": last.key,
        "label": last.label,
        "unit": last.unit,
        "latest": _point(last, origin),
        "previous": _point(prev, origin) if prev else None,
        "change": round(last.value_num - prev.value_num, 3) if prev else None,
        "count": len(history),
        "history": [
            {"date": _iso(h.date_key), "value": h.value_num} for h in history
        ],
    }


def _point(row: Any, origin: Origin) -> dict[str, Any]:
    """One dated value with its source and document."""
    day = _iso(row.date_key)
    return {
        "date": day,
        "value": row.value_num,
        "source": row.source,
        "document": origin.get((row.key, day)),
    }


def _iso(day: date) -> str:
    """ISO date."""
    return day.isoformat()
