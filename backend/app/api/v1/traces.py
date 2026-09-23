"""Import traces from app exports (rides, deliveries, transport, parking)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form, Query, UploadFile

from app.core.deps import SessionDep, UserDep
from app.core.errors import InvalidInputError
from app.services import evidence, trace_store, traces

router = APIRouter(prefix="/traces", tags=["evidence"])


@router.post("/import")
async def import_traces(
    files: list[UploadFile],
    principal: UserDep,
    session: SessionDep,
    kinds: Annotated[list[str], Form()],
    dry_run: Annotated[bool, Query()] = False,
    meals: Annotated[bool, Query()] = False,
    person: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    """Import exports (CSV, Excel, JSON) and receipts (PDF, photo).

    ``kinds`` (same order as the files): transport, taxi, parking,
    livraison, repas, hotel, frais or auto (guessed: a column naming each
    line's kind, a receipt's content). Uber, Uber Eats, Navigo, parking
    apps and expense reports are read by their column titles; a receipt
    met again as an expense line (same kind, day, amount) is merged.
    An expense report PDF (Lucca « Note de frais ») gives one trace per
    expense and keeps the PDF untouched as a document. A ticket export
    (NinjaOne…) gives ``person``'s actions, one trace a day (default:
    the most active author; the preview lists the others).
    ``meals=true`` logs each delivery / meal bought as a meal (with its
    price) for the AI to read. ``dry_run=true`` only reads.
    """
    allowed = {*evidence.TRACES, "auto"}
    if len(kinds) != len(files) or set(kinds) - allowed:
        raise InvalidInputError(f"one kind per file among {sorted(allowed)}")
    batch = [
        (upload.filename or "", kind, await upload.read())
        for upload, kind in zip(files, kinds, strict=True)
    ]
    report, logged = await trace_store.import_traces(
        session,
        principal.user.id,
        batch,
        dry_run=dry_run,
        meals=meals,
        person=person,
    )
    if not dry_run:
        await session.commit()
        for meal in logged:
            await traces.read_meal(session, meal)
    report["meals"] = len(logged)
    return report
