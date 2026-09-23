"""Absences: sick leave, work accident, occupational disease, holidays."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Form, Query, UploadFile, status

from app.core.deps import ReaderDep, SessionDep, UserDep
from app.models.work import Absence
from app.schemas.workfile import AbsenceIn, AbsenceOut
from app.services import absence_import, absences

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
    """Record an absence (arret_maladie, accident_travail, repos…)."""
    row = await absences.save(session, principal.user.id, body.model_dump())
    await session.commit()
    return row


@router.post("/import")
async def import_file(
    files: list[UploadFile],
    principal: UserDep,
    session: SessionDep,
    dry_run: Annotated[bool, Query()] = False,
    person: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    """Import absences from an HR export (Lucca…: CSV, Excel, JSON).

    Start / end days (or one day per row, merged), the kind (congés
    payés, RTT → repos, maladie → arrêt maladie…), the status (refused
    and cancelled rows skipped). A manager's export: ``person`` is kept
    (default: the one with the most rows). Nothing is added twice.
    ``dry_run=true`` only reads.
    """
    batch = [(f.filename or "", await f.read()) for f in files]
    report = await absence_import.store(
        session, principal.user.id, batch, dry_run=dry_run, person=person
    )
    if not dry_run:
        await session.commit()
    return report


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
