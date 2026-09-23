"""Tools: work hours — clock in / out, sessions, stats, import, export."""

from __future__ import annotations

from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def clock_in(at: str | None = None) -> Any:
    """Clock in: start of work (now, or ``at``: ISO date-time).

    A second clock-in while already at work is ignored. A time without
    an offset is the user's local time.
    """
    return await client.post("/work/clock", {"kind": "in", "at": at})


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
    start_at: str,
    end_at: str | None = None,
    note: str = "",
    session_id: str | None = None,
) -> Any:
    """Add a work session, or fix one (``session_id``).

    Times are ISO date-times (local time without an offset). Overlaps and
    sessions over 24 h are refused. Confirm with the user before fixing.
    """
    body = {"start_at": start_at, "end_at": end_at, "note": note}
    if session_id:
        return await client.request(
            "PUT", f"/work/sessions/{session_id}", body=body
        )
    return await client.post("/work/sessions", body)


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

    Default: the last 365 days. Overtime is per week beyond the contract;
    flags: days over 10 h, weeks over 48 h (French legal maximums).
    ``periods`` gives 7 days / 30 days / 3 months / 1 year.
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
