"""Import traces from app exports (rides, deliveries, transport, parking)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form, Query, UploadFile

from app.core.deps import SessionDep, UserDep
from app.core.errors import InvalidInputError
from app.services import evidence, trace_import, traces

router = APIRouter(prefix="/traces", tags=["evidence"])


@router.post("/import")
async def import_traces(
    files: list[UploadFile],
    principal: UserDep,
    session: SessionDep,
    kinds: Annotated[list[str], Form()],
    dry_run: Annotated[bool, Query()] = False,
    meals: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Import CSV / Excel / JSON exports, one kind per file.

    ``kinds`` (same order as the files): transport, taxi, parking,
    livraison, repas, hotel or frais. Uber, Uber Eats, Navigo, parking
    apps and expense reports are read by their column titles.
    ``meals=true`` logs each delivery / meal bought as a meal (with its
    price) for the AI to read. ``dry_run=true`` only reads.
    """
    if len(kinds) != len(files) or set(kinds) - set(evidence.TRACES):
        raise InvalidInputError(
            f"one kind per file among {sorted(evidence.TRACES)}"
        )
    batch = [
        (upload.filename or "", kind, await upload.read())
        for upload, kind in zip(files, kinds, strict=True)
    ]
    report, logged = await trace_import.import_traces(
        session, principal.user.id, batch, dry_run=dry_run, meals=meals
    )
    if not dry_run:
        await session.commit()
        for meal in logged:
            await traces.read_meal(session, meal)
    report["meals"] = len(logged)
    return report
