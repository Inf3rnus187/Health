"""Tools: work hours — clock in / out, sessions, stats, import, export."""

from __future__ import annotations

from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def clock_in(at: str | None = None, remote: bool = False) -> Any:
    """Clock in: start of work (now, or ``at``: ISO date-time).

    ``remote``: working from home ("je bosse à distance") — a session of
    its own, even after a day on site. A second clock-in at the same
    place while at work is ignored. A time without an offset is the
    user's local time.
    """
    place = "remote" if remote else "site"
    return await client.post(
        "/work/clock", {"kind": "in", "at": at, "place": place}
    )


@mcp.tool()
async def clock_out(at: str | None = None) -> Any:
    """Clock out: end of work (now, or ``at``); closes the open session."""
    return await client.post("/work/clock", {"kind": "out", "at": at})


@mcp.tool()
async def work_sessions(
    start: str | None = None, end: str | None = None
) -> Any:
    """Work sessions between two days (default: last 30), newest first."""
    return await client.get("/work/sessions", {"start": start, "end": end})


@mcp.tool()
async def save_work_session(
    start_at: str | None = None,
    end_at: str | None = None,
    note: str = "",
    session_id: str | None = None,
    remote: bool | None = None,
) -> Any:
    """Add a work session, or fix one (``session_id``).

    Times are ISO date-times (local time without an offset); one of the
    two may be missing (completed later). ``remote``: worked from home
    ("j'ai bossé de 21 h à 23 h 30 à distance") — its own session, even
    on a day already worked on site; left out when fixing, the place is
    kept. Overlaps and sessions over 72 h are refused. Confirm with the
    user before fixing.
    """
    body: dict[str, Any] = {
        "start_at": start_at,
        "end_at": end_at,
        "note": note,
    }
    if remote is not None:
        body["place"] = "remote" if remote else "site"
    if session_id:
        return await client.request(
            "PUT", f"/work/sessions/{session_id}", body=body
        )
    return await client.post("/work/sessions", body)


@mcp.tool()
async def work_days(start: str | None = None, end: str | None = None) -> Any:
    """One line per day (default: the last 30 days), oldest first.

    The night before (asleep minutes, awakenings, wake-up), first
    clock-in, last clock-out, hours worked and the remote part, bedtime
    that evening, absence (arret, conge, repos, autre, ferie; ½ for a
    half day), the day's proofs and traces, and the state (complet,
    a_completer, en_cours). The table to read before answering about a
    given day.
    """
    return await client.get("/work/days", {"start": start, "end": end})


@mcp.tool()
async def work_incomplete() -> Any:
    """Days to complete: sessions with a clock-in or clock-out missing.

    Each comes with its context to help the user choose a time: the
    day's proofs and traces (taxi, parking, receipts; the next morning
    too for a missing clock-out), wake-up and bedtime, first and last
    steps, the usual time for that weekday and overall, and the day's
    other sessions (``others``: a lone half with ``merged``, the one
    session both would make; ``free``, a time the missing half may not
    cross). Suggest, never decide: once the user picks a time, fix it
    with save_work_session (``session_id``) and a note saying where the
    time comes from; a lone clock-in or clock-out inside the completed
    session is taken in. Two halves never paired: merge_work_sessions.
    """
    return await client.get("/work/incomplete")


@mcp.tool()
async def merge_work_sessions(session_id: str, other_id: str) -> Any:
    """Make two sessions of the same place one (ask the user first).

    Keeps ``session_id`` with the first clock-in and the last clock-out
    of the two (a lone embauche 09:02 + a lone débauche 19:12 → 09:02 →
    19:12); ``other_id`` is deleted, the note says what it held.
    """
    body = {"other_id": other_id}
    return await client.post(f"/work/sessions/{session_id}/merge", body)


@mcp.tool()
async def delete_work_session(session_id: str) -> Any:
    """Delete one work session (ask the user first)."""
    return await client.request("DELETE", f"/work/sessions/{session_id}")


@mcp.tool()
async def work_stats(
    start: str | None = None,
    end: str | None = None,
    contract_hours: float = 35,
) -> Any:
    """Hours worked: totals, averages, overtime, weeks, months, periods.

    Default: since the first work day. Overtime is per week beyond the
    contract (legal rule); flags: days over 10 h, weeks over 48 h.
    Days off (sick leave, holidays, rest, public holidays) are counted
    (``absences``), left out of the weekly average (full weeks only)
    and taken off each week's target (``beyond_target_hours``);
    ``worked_while_off`` lists days worked during an absence.
    ``periods`` gives 7 days / 30 days / 3 months / 1 year, averaged
    per week present.
    """
    params = {"start": start, "end": end, "contract_hours": contract_hours}
    return await client.get("/work/stats", params)


@mcp.tool()
async def import_work_log(
    text: str, filename: str = "pointage.csv", dry_run: bool = True
) -> Any:
    """Import past clock-in / clock-out logs (txt, csv or json text).

    First call with dry_run=true: it shows what it read (sessions, hours,
    skipped lines); import for real (dry_run=false) once the user agrees.
    Importing twice is harmless (same start = same session).
    """
    flag = "true" if dry_run else "false"
    files = {"file": (filename, text.encode(), "text/plain")}
    return await client.upload(f"/work/import?dry_run={flag}", files, {})


@mcp.tool()
async def export_work(
    level: str = "days",
    export_format: str = "csv",
    start: str | None = None,
    end: str | None = None,
    contract_hours: float = 35,
) -> Any:
    """Work hours as text: level sessions / days / weeks / months, csv or json.

    For a PDF use generate_report(report_type="work").
    """
    params = {
        "level": level,
        "format": export_format,
        "start": start,
        "end": end,
        "contract_hours": contract_hours,
    }
    return await client.get("/work/export", params)
