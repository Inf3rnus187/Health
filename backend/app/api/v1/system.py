"""The hub itself: is an update waiting, and asking the host to install it.

Administrator only: the host's state and its updates concern the whole
hub. Every user's page still sees a new build (``/version.json``) and
offers to reload.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.deps_admin import AdminDep
from app.services import updates

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/update")
async def update_state(principal: AdminDep) -> dict[str, Any]:
    """Changes waiting on GitHub, the parts to rebuild, the last update.

    Written by ``./update.sh`` on the host (``known`` false: it never ran).
    ``watcher``: its cron is active, so « Installer » works.
    """
    del principal
    return updates.state()


@router.post("/update")
async def update_request(principal: AdminDep) -> dict[str, Any]:
    """Ask the host to update now (its cron runs ./update.sh).

    409 when the host's cron is not running ./update.sh --cron.
    """
    return updates.request(principal.user.id)
