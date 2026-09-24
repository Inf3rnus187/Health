"""The facts a report must prove, gathered for one period.

Habits (with the days without an entry and a before / after
comparison), medication adherence, meals, and when and how each entry
was made. The same facts feed the PDF reports and ``GET /facts``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    evidence_habits,
    evidence_meals,
    evidence_trace,
    medication_stats,
)


async def gather(
    session: AsyncSession,
    user_id: str,
    span: tuple[date, date],
    compare_from: date | None = None,
) -> dict[str, Any]:
    """Every fact of ``span`` (compare_from: split the habits there)."""
    adherence = await medication_stats.adherence(session, user_id, span)
    return {
        "start": span[0].isoformat(),
        "end": span[1].isoformat(),
        "compare_from": compare_from.isoformat() if compare_from else None,
        "habits": await evidence_habits.habits(
            session, user_id, span, compare_from
        ),
        "medications": adherence["items"],
        "meals": await evidence_meals.meals(session, user_id, span),
        "trace": await evidence_trace.trace(session, user_id, span),
    }
