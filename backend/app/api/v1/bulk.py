"""Delete many items at once: proofs, sessions, absences, meals, appointments.

Each takes ``{"ids": [...]}`` (5000 at most) and answers how many went;
ids that are not the user's are ignored.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import Principal, SessionDep, UserDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.common import Deleted, EvidenceDeleteIn, IdsIn
from app.services import bulk_delete

router = APIRouter(tags=["bulk"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post("/evidence/delete", response_model=Deleted)
async def evidence(
    body: EvidenceDeleteIn, principal: UserDep, session: SessionDep
) -> dict[str, int]:
    """Delete proofs and traces with their files.

    ``meals``: also the Journal meals the deliveries were logged as.
    """
    done = await bulk_delete.evidence(
        session, principal.user.id, body.ids, body.meals
    )
    await session.commit()
    return done


@router.post("/work/sessions/delete", response_model=Deleted)
async def sessions(
    body: IdsIn, principal: WriteDep, session: SessionDep
) -> dict[str, int]:
    """Delete work sessions and rebuild their days."""
    done = await bulk_delete.sessions(session, principal.user.id, body.ids)
    await session.commit()
    return done


@router.post("/absences/delete", response_model=Deleted)
async def absences(
    body: IdsIn, principal: UserDep, session: SessionDep
) -> dict[str, int]:
    """Delete absences (their evidence stays, unlinked)."""
    done = await bulk_delete.absences(session, principal.user.id, body.ids)
    await session.commit()
    return done


@router.post("/meals/delete", response_model=Deleted)
async def meals(
    body: IdsIn, principal: WriteDep, session: SessionDep
) -> dict[str, int]:
    """Delete meals with their photos and nutrients."""
    gone = await bulk_delete.meals(session, principal.user.id, body.ids)
    await session.commit()
    return {"deleted": gone}


@router.post("/appointments/delete", response_model=Deleted)
async def appointments(
    body: IdsIn, principal: UserDep, session: SessionDep
) -> dict[str, int]:
    """Delete appointments (e.g. the personal events of an imported agenda)."""
    done = await bulk_delete.appointments(session, principal.user.id, body.ids)
    await session.commit()
    return done
