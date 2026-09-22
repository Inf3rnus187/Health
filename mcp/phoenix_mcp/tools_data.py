"""Tools: health data (Apple Health, lab values, entries) and metrics."""

from __future__ import annotations

from datetime import date
from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


def today(day: str | None) -> str:
    """Return ``day`` or today's ISO date."""
    return day or date.today().isoformat()


@mcp.tool()
async def health_summary() -> Any:
    """Home tiles: latest value, 7-day average and change per key metric."""
    return await client.get("/summary")


@mcp.tool()
async def list_domains() -> Any:
    """Domain codes and their French names (Cœur, Biologie, Sommeil…)."""
    return await client.get("/catalog/domains")


@mcp.tool()
async def list_metrics(domain: str | None = None) -> Any:
    """Metric definitions (key, label, unit, domain), optionally by domain."""
    return await client.get("/metrics", {"domain": domain})


@mcp.tool()
async def metric_overview(key: str, days: int = 365) -> Any:
    """One metric exactly as every page shows it.

    Latest reading (time, source), last day, 7/30-day averages, 30-day
    range, sources of the daily values and the daily series.
    """
    return await client.get(f"/metrics/{key}/overview", {"days": days})


@mcp.tool()
async def get_measurements(
    metric_key: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> Any:
    """Daily values (all sources) of a metric between two ISO dates."""
    params = {"metric_key": metric_key, "start": start, "end": end}
    return await client.get("/measurements", params)


@mcp.tool()
async def get_samples(
    metric_key: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> Any:
    """Raw Apple Health samples (each reading with its time and source)."""
    params = {
        "metric_key": metric_key,
        "start": start,
        "end": end,
        "limit": limit,
        "offset": offset,
    }
    return await client.get("/samples", params)


@mcp.tool()
async def get_trend(metric_key: str, bucket: str = "week") -> Any:
    """A metric bucketed by day / week / month (per its aggregation)."""
    return await client.get(
        "/trends", {"metric_key": metric_key, "bucket": bucket}
    )


@mcp.tool()
async def domain_dashboard(domain: str, window: int = 7) -> Any:
    """Dashboard of a domain (body, heart, sleep, bio, habit…)."""
    return await client.get(f"/dashboard/{domain}", {"window": window})


@mcp.tool()
async def daily_summary(date_key: str | None = None) -> Any:
    """Every daily value of one day (default today), with metric names."""
    day = today(date_key)
    rows = await client.get("/measurements", {"start": day, "end": day})
    metrics = {m["id"]: m for m in await client.get("/metrics")}
    return {"date": day, "values": [named(r, metrics) for r in rows]}


def named(row: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """A daily value with its metric key, label and unit."""
    metric = metrics.get(row["metric_id"], {})
    value = next(
        (
            row[k]
            for k in ("value_num", "value_text", "value_bool")
            if row.get(k) is not None
        ),
        row.get("value_time") or row.get("value_json"),
    )
    return {
        "key": metric.get("key"),
        "label": metric.get("label"),
        "unit": metric.get("unit"),
        "value": value,
        "source": row.get("source"),
    }


@mcp.tool()
async def data_inventory() -> Any:
    """Everything stored, per metric and source.

    Raw and daily counts by source with their first/last dates: checks
    that Apple, Health Auto Export and lab values agree.
    """
    return await client.get("/data/inventory")


@mcp.tool()
async def reconcile_data() -> Any:
    """Rebuild one truth from the stored data (no AI).

    Merges duplicate keys, aligns with the HealthKit catalog and
    recomputes every daily value from raw samples (in the worker).
    """
    return await client.post("/data/reconcile")


@mcp.tool()
async def record_measurement(
    metric_key: str, value: Any, date_key: str | None = None
) -> Any:
    """Record one value (weight, cigarettes, symptom…); idempotent per day."""
    item = {
        "metric_key": metric_key,
        "date_key": today(date_key),
        "value": value,
    }
    return await client.post("/measurements", {"items": [item]})


@mcp.tool()
async def delete_measurement(measurement_id: str) -> Any:
    """Delete one recorded daily value by id."""
    return await client.request("DELETE", f"/measurements/{measurement_id}")


@mcp.tool()
async def create_metric(
    key: str,
    label: str,
    domain: str,
    data_type: str = "float",
    unit: str | None = None,
    aggregation_hint: str = "avg",
) -> Any:
    """Create a custom metric (e.g. habit.patches) — no migration needed."""
    body = {
        "key": key,
        "label": label,
        "domain": domain,
        "data_type": data_type,
        "unit": unit,
        "aggregation_hint": aggregation_hint,
    }
    return await client.post("/metrics", body)


@mcp.tool()
async def update_metric(key: str, changes: dict[str, Any]) -> Any:
    """Change a metric's label, unit, bounds, aggregation or active flag."""
    return await client.request("PATCH", f"/metrics/{key}", body=changes)


@mcp.tool()
async def export_data(
    export_format: str = "csv",
    domain: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> Any:
    """Export tidy data as text (csv / json / fhir)."""
    params = {
        "format": export_format,
        "domain": domain,
        "from": start,
        "to": end,
    }
    return await client.get("/export", params)
