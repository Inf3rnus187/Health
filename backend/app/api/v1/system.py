"""The hub itself: is an update waiting, and asking the host to install it.

Administrator only: the host's state and its updates concern the whole
hub. Every user's page still sees a new build (``/version.json``) and
offers to reload.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.deps import PrincipalDep
from app.core.deps_admin import AdminDep
from app.services import updates

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/version")
async def version(principal: PrincipalDep) -> dict[str, Any]:
    """The version the hub runs (any signed-in user; no host detail).

    ``commit``: the host's last finished update, else the commit it last
    saw, else the API's build; ``installed_at``: when that update
    finished; ``api``: the commit the API itself was built from. A
    change of the server alone does not rebuild the page, so this, not
    the page's own build, says what is installed.
    """
    del principal
    return updates.installed()


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
