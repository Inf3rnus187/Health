"""The hub's administrator: host-level actions (updates, users, settings)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.deps import InteractiveDep, Principal
from app.core.errors import ForbiddenError

#: The role of the hub's administrator (other accounts: « user »).
ADMIN_ROLE = "admin"


async def get_admin_principal(principal: InteractiveDep) -> Principal:
    """Require the administrator's interactive session (never a token)."""
    if principal.user.role != ADMIN_ROLE:
        raise ForbiddenError("Administrator only")
    return principal


AdminDep = Annotated[Principal, Depends(get_admin_principal)]
