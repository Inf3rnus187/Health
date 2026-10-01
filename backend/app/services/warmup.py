"""Each API process readies its first sync when it starts.

After an update, the first sync each API process handled was the slow
one (212 ms at the user's, 32 ms the next): its database connection to
open, its statements to prepare, its code to run once. When a process
starts (before it answers, after the migrations), it now opens one
connection — the one its syncs then reuse, coming one at a time — and
runs a sync's reads on it for an account that cannot exist
(:func:`app.services.healthkit_sync.warm`), with the token's lookup,
then rolls back: nothing is written, no account's data is read.
``API_WARMUP=false`` turns it off. A failure is logged and never stops
the process from starting.
"""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.deps import _from_token
from app.core.logging import get_logger
from app.services import healthkit_sync

_log = get_logger("warmup")


async def run() -> None:
    """Ready this process's connection and first sync (logged)."""
    if not get_settings().api_warmup:
        return
    started = time.perf_counter()
    try:
        async with SessionFactory() as session:
            await _from_token(session, "phoenix-warmup")  # no such token
            await healthkit_sync.warm(session)
            await session.rollback()
    except Exception:  # never keep the API from starting
        _log.warning("warmup_failed", exc_info=True)
        return
    ms = round((time.perf_counter() - started) * 1000)
    _log.info("warmed", ms=ms)
