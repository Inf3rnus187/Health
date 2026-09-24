"""Medication intakes: record a dose, list them, delete a mistake.

A dose belongs to one of the user's treatments (found by id, or by name
for an iPhone Shortcut: accents and case ignored). It is dated in the
user's local day; its channel comes from the caller — the web session,
an MCP client (``hub:full`` token), another token (a Shortcut) — with
the token's id, and ``created_at`` keeps when it was entered.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import InvalidInputError, NotFoundError
from app.core.scopes import HUB_FULL
from app.models.base import utcnow
from app.models.medical import Treatment
from app.models.medication import MedicationIntake
from app.schemas.medication import IntakeIn
from app.services.daily_rollup import user_zone
from app.services.text_norm import norm
from app.services.timed_entries import day_bounds, utc

_FUTURE = timedelta(minutes=10)
_SHORTEST_PART = 3


async def record(
    session: AsyncSession, who: Principal, treatment: Treatment, data: IntakeIn
) -> MedicationIntake:
    """One dose of ``treatment``, now or at ``data.taken_at``."""
    zone = await user_zone(session, who.user.id)
    at = data.taken_at or utcnow()
    if at.tzinfo is None:  # a local time typed in a form
        at = at.replace(tzinfo=zone)
    if utc(at) > utcnow() + _FUTURE:
        raise InvalidInputError("A dose cannot be in the future")
    intake = MedicationIntake(
        user_id=who.user.id,
        treatment_id=treatment.id,
        name=treatment.name,
        dose=(data.dose or treatment.dose or "")[:80],
        taken_at=utc(at),
        date_key=utc(at).astimezone(zone).date(),
        status=data.status,
        source=_channel(who),
        token_id=who.token_id,
        note=data.note.strip(),
    )
    session.add(intake)
    await session.flush()
    return intake


async def treatment_named(
    session: AsyncSession, user_id: str, name: str
) -> Treatment:
    """The user's treatment called ``name`` (active ones first), or 404.

    The whole name first, else (3 letters or more) a treatment with a
    word starting so (« parox » finds « Paroxétine 20 mg »).
    """
    known = await _all(session, user_id)
    wanted = norm(name)
    found = [t for t in known if norm(t.name) == wanted]
    if not found and len(wanted) >= _SHORTEST_PART:
        found = [t for t in known if f" {wanted}" in f" {norm(t.name)}"]
    if not found:
        raise NotFoundError(f"No treatment called « {name} »")
    return sorted(found, key=lambda t: not t.active)[0]


async def list_intakes(
    session: AsyncSession,
    user_id: str,
    span: tuple[date, date],
    treatment_id: str | None = None,
) -> list[MedicationIntake]:
    """The doses of ``span`` (local days), newest first."""
    zone = await user_zone(session, user_id)
    stmt = select(MedicationIntake).where(
        MedicationIntake.user_id == user_id,
        MedicationIntake.taken_at >= day_bounds(span[0], zone)[0],
        MedicationIntake.taken_at < day_bounds(span[1], zone)[1],
    )
    if treatment_id:
        stmt = stmt.where(MedicationIntake.treatment_id == treatment_id)
    rows = await session.execute(
        stmt.order_by(MedicationIntake.taken_at.desc())
    )
    return list(rows.scalars())


async def delete(session: AsyncSession, user_id: str, intake_id: str) -> None:
    """Delete one of the user's doses (a mistake; the audit log keeps it)."""
    intake = await session.get(MedicationIntake, intake_id)
    if intake is None or intake.user_id != user_id:
        raise NotFoundError("Intake not found")
    await session.delete(intake)
    await session.flush()


async def _all(session: AsyncSession, user_id: str) -> list[Treatment]:
    """Every treatment of the user."""
    rows = await session.execute(
        select(Treatment).where(Treatment.user_id == user_id)
    )
    return list(rows.scalars())


def _channel(who: Principal) -> str:
    """How the dose came in: web, mcp or raccourci (another token)."""
    if who.source == "jwt":
        return "web"
    return "mcp" if HUB_FULL in who.scopes else "raccourci"


def as_dict(intake: MedicationIntake) -> dict[str, Any]:
    """A dose for the audit log (no free text)."""
    return {"treatment": intake.name, "status": intake.status}
