"""Best-effort enqueue of background jobs to the ARQ worker.

If Redis/the worker is unavailable the call fails softly: the caller
stays responsive and the job can be retried/reprocessed later.
"""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger("queue")


async def enqueue(function: str, *args: Any) -> bool:
    """Enqueue ``function`` with ``args``; return whether it was queued."""
    return await enqueue_many(function, [args]) == 1


async def enqueue_many(function: str, calls: list[tuple[Any, ...]]) -> int:
    """Enqueue one job per argument tuple over one connection; count them."""
    queued = 0
    try:
        pool = await create_pool(
            RedisSettings.from_dsn(get_settings().redis_url)
        )
        for args in calls:
            await pool.enqueue_job(function, *args)
            queued += 1
        await pool.aclose()
    except Exception as exc:  # noqa: BLE001
        _log.warning("enqueue_failed", function=function, error=str(exc))
    return queued
