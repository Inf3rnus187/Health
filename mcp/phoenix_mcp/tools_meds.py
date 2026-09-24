"""Tools: medication doses (taken or not) and adherence."""

from __future__ import annotations

from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def log_medication(
    treatment: str,
    taken_at: str | None = None,
    status: str = "taken",
    note: str = "",
) -> Any:
    """Record a dose of a treatment, by its name (part of it is enough).

    ``taken_at``: ISO date-time (default now; without offset: local).
    ``status``: ``taken`` or ``skipped`` (not taken: forgotten, refused…).
    The dose keeps when it was entered and that it came from MCP.
    """
    body = {
        "treatment": treatment,
        "taken_at": taken_at,
        "status": status,
        "note": note,
    }
    return await client.post("/medications/take", body)


@mcp.tool()
async def medications_today() -> Any:
    """Active treatments with today's doses (taken, not taken, last)."""
    return await client.get("/medications/today")


@mcp.tool()
async def medication_intakes(
    start: str | None = None,
    end: str | None = None,
    treatment_id: str | None = None,
) -> Any:
    """Doses of a period (default: last 30 days), newest first.

    Each: when taken, when entered (``created_at``), how (``source``:
    web, raccourci, mcp), taken or not.
    """
    return await client.get(
        "/medications/intakes",
        {"start": start, "end": end, "treatment_id": treatment_id},
    )


@mcp.tool()
async def medication_adherence(
    start: str | None = None, end: str | None = None
) -> Any:
    """Adherence per treatment (default: last 30 days).

    Planned doses, taken, not taken, rate %, days complete, days without
    any record, longest gap, usual time, doses entered late, per week.
    """
    return await client.get(
        "/medications/adherence", {"start": start, "end": end}
    )


@mcp.tool()
async def delete_medication_intake(intake_id: str) -> Any:
    """Delete a dose entered by mistake (the audit log keeps a trace)."""
    return await client.request("DELETE", f"/medications/intakes/{intake_id}")
