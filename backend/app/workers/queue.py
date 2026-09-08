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
    try:
        pool = await create_pool(
            RedisSettings.from_dsn(get_settings().redis_url)
        )
        await pool.enqueue_job(function, *args)
        await pool.aclose()
    except Exception as exc:  # noqa: BLE001
        _log.warning("enqueue_failed", function=function, error=str(exc))
        return False
    return True
