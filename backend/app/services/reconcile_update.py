"""Each user's history reconciled once after an update of the hub.

A new version (GIT_COMMIT) may change the catalogue (two keys merged) or
the day's rule. The syncs recompute only the days they touch, so older
days would keep the old reading until « Réconcilier ». The worker checks
RECONCILE_AFTER_UPDATE_DELAY_S after it starts (the API applies the
migrations meanwhile), then every hour: each active user whose last
reconcile ran on another version is reconciled, one after the other, in
the background. A reconcile that fails is tried again the next hour;
one that ran (by hand too) is not repeated for the same version.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User
from app.services import reconcile

_log = get_logger("reconcile_update")
#: The start's check and the hourly one never run at the same time.
_ONE_AT_A_TIME = asyncio.Lock()


async def pending(session: AsyncSession) -> list[str]:
    """The active users not yet reconciled on this version."""
    commit = get_settings().git_commit
    if not commit or not get_settings().reconcile_after_update:
        return []
    result = await session.execute(
        select(User.id).where(
            User.is_active.is_(True),
            or_(
                User.reconciled_commit.is_(None),
                User.reconciled_commit != commit,
            ),
        )
    )
    return list(result.scalars().all())


async def run_pending(sessions: Callable[[], Any]) -> int:
    """Reconcile each pending user in turn; how many were reconciled."""
    async with _ONE_AT_A_TIME:
        try:
            async with sessions() as session:
                users = await pending(session)
        except Exception as exc:  # noqa: BLE001 - migrations not applied yet
            _log.warning("reconcile_after_update_waiting", error=str(exc))
            return 0
        done = 0
        for user_id in users:
            done += await _one(sessions, user_id)
        return done


async def _one(sessions: Callable[[], Any], user_id: str) -> int:
    """One user's reconcile (1), or its failure logged (0)."""
    try:
        async with sessions() as session:
            await reconcile.run(session, user_id)
    except Exception as exc:  # noqa: BLE001 - the next hour tries again
        _log.warning("reconcile_after_update_failed", user_id=user_id,
                     error=str(exc))  # fmt: skip
        return 0
    return 1
