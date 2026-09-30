"""Raw samples per metric and source, from the counts the database keeps.

The triggers of :mod:`app.models.sample_counts` keep the counts exact;
:func:`rebuild` recomputes them from the samples (migration 0027,
« Réconcilier »), a check that costs what counting did before (0.3 s on
2.4 million samples).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sample_counts import REFILL, counts


async def of_user(session: AsyncSession, user_id: str) -> list[Any]:
    """``(metric_id, source, count, first, last)`` per metric and source."""
    result = await session.execute(
        select(
            counts.c.metric_id,
            counts.c.source,
            counts.c.n,
            counts.c.first_at,
            counts.c.last_at,
        ).where(counts.c.user_id == user_id)
    )
    return list(result.all())


async def rebuild(session: AsyncSession, user_id: str) -> None:
    """Recompute a user's counts from their samples (in the transaction).

    PostgreSQL: the samples are locked against writes meanwhile (a sync
    waits a fraction of a second), so no write falls between the two.
    """
    if session.bind.dialect.name == "postgresql":
        await session.execute(text("LOCK TABLE health_samples IN SHARE MODE"))
    await session.execute(delete(counts).where(counts.c.user_id == user_id))
    await session.execute(
        text(REFILL.format(where="WHERE user_id = :user")), {"user": user_id}
    )
