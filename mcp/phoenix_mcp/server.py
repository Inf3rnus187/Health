"""Phoenix Health Hub MCP server: hub tools over MCP (§9).

Each tool is a thin wrapper over the REST API so there is a single source
of truth. Configure ``API_BASE_URL`` and ``PHOENIX_API_TOKEN``; run with
``python -m phoenix_mcp.server`` (transport via ``MCP_TRANSPORT``).
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from phoenix_mcp import client

mcp = FastMCP(
    "phoenix-health-hub",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "9000")),
)


def _today(day: str | None) -> str:
    """Return ``day`` or today's ISO date."""
    return day or date.today().isoformat()


def _summarize(day: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Group a day's measurements by metric for a compact summary."""
    values = {row["metric_id"]: row.get("value") for row in rows}
    return {"date": day, "count": len(rows), "values": values}


@mcp.tool()
async def list_metrics(domain: str | None = None) -> list[dict[str, Any]]:
    """List metric definitions, optionally filtered by domain."""
    params = {"domain": domain} if domain else None
    result: list[dict[str, Any]] = await client.get("/metrics", params)
    return result


@mcp.tool()
async def create_metric(
    key: str,
    label: str,
    domain: str,
    data_type: str,
    unit: str | None = None,
) -> dict[str, Any]:
    """Create a new metric definition at runtime (no migration)."""
    body = {
        "key": key,
        "label": label,
        "domain": domain,
        "data_type": data_type,
        "unit": unit,
    }
    created: dict[str, Any] = await client.post("/metrics", body)
    return created


@mcp.tool()
async def record_measurement(
    metric_key: str, value: Any, date_key: str | None = None
) -> list[dict[str, Any]]:
    """Record one measurement (date defaults to today; idempotent)."""
    item = {
        "metric_key": metric_key,
        "date_key": _today(date_key),
        "value": value,
    }
    rows: list[dict[str, Any]] = await client.post(
        "/measurements", {"items": [item]}
    )
    return rows


@mcp.tool()
async def get_measurements(
    metric_key: str, start: str | None = None, end: str | None = None
) -> list[dict[str, Any]]:
    """Return raw measurements for a metric over an optional period."""
    params: dict[str, Any] = {"metric_key": metric_key}
    if start:
        params["from"] = start
    if end:
        params["to"] = end
    rows: list[dict[str, Any]] = await client.get("/measurements", params)
    return rows


@mcp.tool()
async def get_trend(
    metric_key: str, agg: str = "avg", window: int = 7
) -> dict[str, Any]:
    """Return a rolling-aggregated trend series for a metric."""
    params = {"metric_key": metric_key, "agg": agg, "window": window}
    series: dict[str, Any] = await client.get("/measurements/series", params)
    return series


@mcp.tool()
async def get_daily_summary(date_key: str | None = None) -> dict[str, Any]:
    """Summarize every measurement recorded on a given day."""
    day = _today(date_key)
    rows = await client.get("/measurements", {"from": day, "to": day})
    return _summarize(day, rows)


@mcp.tool()
async def get_photo_analysis(photo_id: str) -> dict[str, Any]:
    """Return the AI analysis for a photo."""
    found: dict[str, Any] = await client.get(f"/photos/{photo_id}/analysis")
    return found


@mcp.tool()
async def compare_photos(from_id: str, to_id: str) -> dict[str, Any]:
    """Compare two photos and return both analyses."""
    comparison: dict[str, Any] = await client.get(
        "/photos/compare", {"from": from_id, "to": to_id}
    )
    return comparison


@mcp.tool()
async def generate_report(
    report_type: str = "clinical_pdf",
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Generate a report (clinical_pdf/csv/json/xlsx/fhir)."""
    body = {
        "type": report_type,
        "period_start": period_start,
        "period_end": period_end,
    }
    report: dict[str, Any] = await client.post("/reports", body)
    return report


@mcp.tool()
async def export_data(
    export_format: str = "csv", domain: str | None = None
) -> str:
    """Export tidy data as text (csv/json/fhir)."""
    params: dict[str, Any] = {"format": export_format}
    if domain:
        params["domain"] = domain
    return await client.get_text("/export", params)


@mcp.tool()
async def list_automations() -> list[dict[str, Any]]:
    """List the user's automations."""
    rows: list[dict[str, Any]] = await client.get("/automations")
    return rows


@mcp.tool()
async def create_automation(
    name: str, trigger: str, action: dict[str, Any]
) -> dict[str, Any]:
    """Create an automation (trigger nfc/shortcut/manual/schedule/api)."""
    body = {"name": name, "trigger": trigger, "action": action}
    created: dict[str, Any] = await client.post("/automations", body)
    return created


def main() -> None:
    """Run the MCP server with the configured transport."""
    mcp.run(transport=_transport())


def _transport() -> Any:
    """Return the configured MCP transport name."""
    return os.environ.get("MCP_TRANSPORT", "sse")


if __name__ == "__main__":
    main()
