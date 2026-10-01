"""Python's garbage collector told to skip the objects that live forever.

An API process holds hundreds of thousands of objects for its whole life
(routes, schemas, the ORM's tables). Each full collection used to walk
all of them again: 80 to 110 ms added to an answer that builds many
objects (a dashboard of 14 600 points, docs/performance.md). Once the
process is started, they are frozen (``gc.freeze``): collections walk
only the objects of the requests. Nothing a request makes is kept any
longer. Thawed at shutdown so the process ends cleanly. ``GC_FREEZE=
false`` turns it off.

The time the process spends in collections is added up
(:func:`collected`): a sync's trace says how much of it fell during the
sync (``gc``) — a pause that lands inside any of its steps.
"""

from __future__ import annotations

import gc
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

from app.core.config import get_settings

#: Seconds spent in collections since the process started, and the start
#: of the collection under way.
_spent = [0.0]
_began: list[float] = []


def _clock(phase: str, info: dict[str, Any]) -> None:
    """Add up each collection's time (one of ``gc.callbacks``)."""
    del info
    if phase == "start":
        _began.append(perf_counter())
    elif _began:
        _spent[0] += perf_counter() - _began.pop()


gc.callbacks.append(_clock)


def collected() -> float:
    """Seconds this process has spent in garbage collections so far."""
    return _spent[0]


def freeze() -> None:
    """Collect once, then leave every object alive now out of collections."""
    if get_settings().gc_freeze:
        gc.collect()
        gc.freeze()


def thaw() -> None:
    """Give the frozen objects back to the collector (at shutdown)."""
    gc.unfreeze()


@asynccontextmanager
async def lifespan(_: Any) -> AsyncIterator[None]:
    """The API's life: frozen once started, thawed when it stops."""
    freeze()
    yield
    thaw()
