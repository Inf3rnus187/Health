"""Absences: sick leave, work accident, occupational disease, holidays."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import ReaderDep, SessionDep, UserDep
from app.models.work import Absence
from app.schemas.workfile import AbsenceIn, AbsenceOut
from app.services import absences

router = APIRouter(prefix="/absences", tags=["absences"])


@router.get("", response_model=list[AbsenceOut])
async def index(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[Absence]:
    """Absences overlapping two days (all by default), oldest first."""
    return await absences.list_absences(session, principal.user.id, start, end)


@router.post("", response_model=AbsenceOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: AbsenceIn, principal: UserDep, session: SessionDep
) -> Absence:
    """Record an absence (kind: arret_maladie, accident_travail…)."""
    row = await absences.save(session, principal.user.id, body.model_dump())
    await session.commit()
    return row


@router.put("/{absence_id}", response_model=AbsenceOut)
async def replace(
    absence_id: str, body: AbsenceIn, principal: UserDep, session: SessionDep
) -> Absence:
    """Replace an absence's dates, kind, cause and note."""
    row = await absences.save(
        session, principal.user.id, body.model_dump(), absence_id
    )
    await session.commit()
    return row


@router.delete("/{absence_id}")
async def remove(
    absence_id: str, principal: UserDep, session: SessionDep
) -> dict[str, str]:
    """Delete an absence (its evidence stays)."""
    await absences.delete(session, principal.user.id, absence_id)
    await session.commit()
    return {"detail": "deleted"}
