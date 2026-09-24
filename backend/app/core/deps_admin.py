"""The hub's administrator: host-level actions (updates, users, settings)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.deps import InteractiveDep, Principal, require_scope
from app.core.errors import ForbiddenError
from app.core.scopes import WRITE_METRICS

#: The role of the hub's administrator (other accounts: « user »).
ADMIN_ROLE = "admin"


async def get_admin_principal(principal: InteractiveDep) -> Principal:
    """Require the administrator's interactive session (never a token)."""
    if principal.user.role != ADMIN_ROLE:
        raise ForbiddenError("Administrator only")
    return principal


AdminDep = Annotated[Principal, Depends(get_admin_principal)]


async def get_catalog_editor(
    principal: Annotated[Principal, Depends(require_scope(WRITE_METRICS))],
) -> Principal:
    """An administrator (session or ``write:metrics`` token) only.

    The metric catalogue is shared by every user: a change of unit,
    bounds or « active » would change everybody's data.
    """
    if principal.user.role != ADMIN_ROLE:
        raise ForbiddenError(
            "The metric catalogue is shared: administrator only"
        )
    return principal


CatalogDep = Annotated[Principal, Depends(get_catalog_editor)]
