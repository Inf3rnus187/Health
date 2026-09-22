"""Tools: reports and AI synthesis, automations, direct API access."""

from __future__ import annotations

from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def generate_report(
    report_type: str = "synthesis",
    period_start: str | None = None,
    period_end: str | None = None,
) -> Any:
    """Generate a report, then poll get_report.

    Types: synthesis (AI clinical synthesis + clinical PDF, takes
    minutes), clinical_pdf, csv, json, xlsx, fhir.
    """
    body = {
        "type": report_type,
        "period_start": period_start,
        "period_end": period_end,
    }
    return await client.request(
        "POST", "/reports", body=body, timeout=client.LONG
    )


@mcp.tool()
async def list_reports() -> Any:
    """Recent reports with their status (and synthesis when present)."""
    return await client.get("/reports")


@mcp.tool()
async def get_report(report_id: str) -> Any:
    """One report, with its AI synthesis when present.

    Each kept sentence cites the numbered facts of the record; the
    rejected sentences are listed with the reason.
    """
    return await client.get(f"/reports/{report_id}")


@mcp.tool()
async def list_automations() -> Any:
    """The user's automations (NFC, shortcut, schedule…)."""
    return await client.get("/automations")


@mcp.tool()
async def create_automation(
    name: str, trigger: str, action: dict[str, Any]
) -> Any:
    """Create an automation (trigger: nfc/shortcut/manual/schedule/api)."""
    body = {"name": name, "trigger": trigger, "action": action}
    return await client.post("/automations", body)


@mcp.tool()
async def run_automation(automation_id: str) -> Any:
    """Run an automation now."""
    return await client.post(f"/automations/{automation_id}/run")


@mcp.tool()
async def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Read any API route not covered by a tool.

    E.g. /metrics/body.weight or /events; ``path`` is relative to
    /api/v1 (see /openapi.json).
    """
    return await client.get(path, params)


@mcp.tool()
async def api_call(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """Call any API route (POST/PUT/PATCH/DELETE) not covered.

    Destructive routes act on real health data: confirm with the user.
    """
    return await client.request(method.upper(), path, params=params, body=body)
