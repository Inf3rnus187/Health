"""Medication intakes: each dose taken or not, and the adherence.

A dose comes from the web page, an iPhone Shortcut (``?token=`` with
``write:measurements``, by the treatment's name), MCP or the API; each
keeps when it was taken, when it was entered and how.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import (
    Principal,
    ReaderDep,
    SessionDep,
    require_scope,
)
from app.core.deps_query import require_scope_flex
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.medication import MedicationIntake
from app.schemas.medication import IntakeIn, IntakeOut, TakeIn
from app.services import audit, medication_stats, medications
from app.services import treatments as treatment_service

router = APIRouter(tags=["care"])

TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]
WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]
_DAYS = 30


@router.post(
    "/treatments/{tid}/intakes",
    response_model=IntakeOut,
    status_code=status.HTTP_201_CREATED,
)
async def add(
    tid: str, body: IntakeIn, principal: TapDep, session: SessionDep
) -> MedicationIntake:
    """Record a dose of a treatment: now, or ``taken_at``.

    ``status``: ``taken`` (default) or ``skipped`` (not taken: forgotten,
    refused… — declaring it is part of an honest record).
    """
    treatment = await treatment_service.get(session, principal.user.id, tid)
    return await _record(session, principal, treatment, body)


@router.post(
    "/medications/take",
    response_model=IntakeOut,
    status_code=status.HTTP_201_CREATED,
)
async def take(
    body: TakeIn, principal: TapDep, session: SessionDep
) -> MedicationIntake:
    """Record a dose by the treatment's name (an iPhone Shortcut).

    JSON ``{"treatment": "Paroxétine"}`` (accents and case ignored; part
    of the name is enough), and optionally ``taken_at``, ``status``
    (``skipped``: not taken), ``note``. Works with ``?token=``.
    """
    treatment = await medications.treatment_named(
        session, principal.user.id, body.treatment
    )
    return await _record(session, principal, treatment, body)


@router.get("/medications/intakes", response_model=list[IntakeOut])
async def intakes(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    treatment_id: Annotated[str | None, Query()] = None,
) -> list[MedicationIntake]:
    """The doses of a period (default: the last 30 days), newest first.

    Each: when taken, when entered (``created_at``), how (``source``:
    web, raccourci, mcp), taken or not.
    """
    span = await medication_stats.span(session, principal.user.id, start, end)
    return await medications.list_intakes(
        session, principal.user.id, span, treatment_id
    )


@router.delete("/medications/intakes/{intake_id}")
async def delete(
    intake_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Delete a dose entered by mistake (the audit log keeps the trace)."""
    await medications.delete(session, principal.user.id, intake_id)
    await audit.record(
        session,
        action="delete",
        entity="medication_intake",
        user_id=principal.user.id,
        entity_id=intake_id,
    )
    await session.commit()
    return {"detail": "deleted"}


async def _record(
    session: SessionDep, principal: Principal, treatment: Any, body: IntakeIn
) -> MedicationIntake:
    """Record, audit and commit one dose."""
    intake = await medications.record(session, principal, treatment, body)
    await audit.record(
        session,
        action="create",
        entity="medication_intake",
        user_id=principal.user.id,
        entity_id=intake.id,
        source=intake.source,
        payload=medications.as_dict(intake),
    )
    await session.commit()
    return intake
