"""Import one-event-per-line logs (Shortcut history files)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Query, UploadFile

from app.core.deps import Principal, SessionDep
from app.core.deps_query import require_scope_flex
from app.core.scopes import WRITE_MEASUREMENTS
from app.services import log_import

router = APIRouter(prefix="/logs", tags=["logs"])

TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]


@router.post("/import")
async def import_logs(
    files: list[UploadFile],
    principal: TapDep,
    session: SessionDep,
    keys: Annotated[list[str] | None, Form()] = None,
    dry_run: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Import Shortcut logs: one time stamp per line, one kind per file.

    ``keys`` (same order as the files; empty = from the file name):
    work.start, work.end, elimination.urination, habit.cigarettes,
    habit.coffee, habit.urges_broken, water.bottles_1_5. Clock-ins and
    clock-outs sent together are paired. ``dry_run=true`` only reads.
    """
    given = list(keys or [])
    batch = [
        (
            upload.filename or "",
            (given[i] if i < len(given) else "") or None,
            await upload.read(),
        )
        for i, upload in enumerate(files)
    ]
    report = await log_import.import_logs(
        session, principal.user.id, batch, dry_run=dry_run
    )
    if not dry_run:
        await session.commit()
    return report
