"""Evidence: calls, messages, mails, screenshots, notes, documents."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.core.deps import ReaderDep, SessionDep, UserDep
from app.core.errors import InvalidInputError, NotFoundError
from app.models.work import Evidence
from app.schemas.workfile import EvidenceOut, EvidenceUpdate
from app.services import evidence, trace_columns, traces
from app.services.daily_rollup import user_zone

router = APIRouter(prefix="/evidence", tags=["evidence"])

_MAX_BYTES = 30 * 1024 * 1024


@router.get("", response_model=list[EvidenceOut])
async def index(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[Evidence]:
    """Proofs and traces between two days (all by default), oldest first."""
    return await evidence.list_items(session, principal.user.id, start, end)


def _form(
    occurred_at: Annotated[datetime, Form()],
    kind: Annotated[str, Form()] = "capture",
    title: Annotated[str, Form(max_length=200)] = "",
    description: Annotated[str, Form(max_length=8000)] = "",
    count: Annotated[int, Form(ge=1, le=10000)] = 1,
    absence_id: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    """The item's details from the form."""
    if kind not in evidence.KINDS:
        raise InvalidInputError(f"kind must be one of {sorted(evidence.KINDS)}")
    return {
        "occurred_at": occurred_at,
        "kind": kind,
        "title": title,
        "description": description,
        "count": count,
        "absence_id": absence_id or None,
    }


def _trace(
    ended_at: Annotated[str, Form()] = "",
    place: Annotated[str, Form(max_length=300)] = "",
    amount: Annotated[str, Form(max_length=40)] = "",
    currency: Annotated[str, Form(min_length=3, max_length=3)] = "EUR",
    meal: Annotated[bool, Form()] = False,
) -> dict[str, Any]:
    """What a trace adds: end, place, amount, and "log it as a meal".

    Empty fields (a web form sends them) mean "not given".
    """
    try:
        end = datetime.fromisoformat(ended_at) if ended_at.strip() else None
    except ValueError as exc:
        raise InvalidInputError("ended_at must be an ISO date-time") from exc
    return {
        "ended_at": end,
        "place": place.strip(),
        "amount": trace_columns.amount(amount) if amount.strip() else None,
        "currency": currency.upper(),
        "meal": meal,
    }


@router.post(
    "", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED
)
async def create(
    principal: UserDep,
    session: SessionDep,
    fields: Annotated[dict[str, Any], Depends(_form)],
    trace: Annotated[dict[str, Any], Depends(_trace)],
    file: UploadFile | None = None,
) -> Evidence:
    """Add a proof or a trace (file optional): when, what, how many.

    A delivered or bought meal (``meal=true``) is also logged as a meal,
    with its price, and read by the AI.
    """
    tz = await user_zone(session, principal.user.id)
    as_meal = trace.pop("meal") and fields["kind"] in traces.MEAL_KINDS
    fields["occurred_at"] = _utc(fields["occurred_at"], tz)
    if trace["ended_at"] is not None:
        trace["ended_at"] = _utc(trace["ended_at"], tz)
    row = await evidence.create(
        session, principal.user.id, {**fields, **trace}, await _upload(file)
    )
    meal = await traces.add_meal(session, row, "") if as_meal else None
    await session.commit()
    if meal is not None:
        await traces.read_meal(session, meal)
    return row


async def _upload(file: UploadFile | None) -> tuple[str, str, bytes] | None:
    """The uploaded file (name, media type, bytes), 30 MB at most."""
    if file is None or not file.filename:
        return None
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise InvalidInputError("File over 30 MB")
    return file.filename, file.content_type or "", data


def _utc(value: datetime, tz: ZoneInfo) -> datetime:
    """A form time in UTC (without offset: the user's local time)."""
    aware = value if value.tzinfo else value.replace(tzinfo=tz)
    return aware.astimezone(UTC)


@router.get("/{item_id}/file")
async def download(
    item_id: str, principal: ReaderDep, session: SessionDep
) -> Response:
    """The item's file, as received."""
    row = await evidence.get(session, principal.user.id, item_id)
    data = evidence.read_file(row)
    if data is None:
        raise NotFoundError("No file for this evidence")
    name = (row.file_name or "preuve").replace('"', "")
    return Response(
        content=data,
        media_type=row.media_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


@router.put("/{item_id}", response_model=EvidenceOut)
async def edit(
    item_id: str,
    body: EvidenceUpdate,
    principal: UserDep,
    session: SessionDep,
) -> Evidence:
    """Fix an item's details (its file and fingerprint do not change)."""
    row = await evidence.get(session, principal.user.id, item_id)
    changes = body.model_dump(exclude_unset=True)
    tz = await user_zone(session, principal.user.id)
    for key in ("occurred_at", "ended_at"):
        if changes.get(key) is not None:
            changes[key] = _utc(changes[key], tz)
    for key, value in changes.items():
        setattr(row, key, value)
    await session.commit()
    return row


@router.delete("/{item_id}")
async def remove(
    item_id: str, principal: UserDep, session: SessionDep
) -> dict[str, str]:
    """Delete an item and its file."""
    await evidence.delete(session, principal.user.id, item_id)
    await session.commit()
    return {"detail": "deleted"}
