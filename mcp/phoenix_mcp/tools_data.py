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
    """Home tiles: latest value, 7-day average and change per key metric.

    ``at``: time of the last reading (a counter's last addition); the
    kcal eaten (nutrition.energy, from analysed meals) sit next to active
    and resting energy — spent = active + resting.
    """
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
    return {
        "key": metric.get("key"),
        "label": metric.get("label"),
        "unit": metric.get("unit"),
        "value": value_of(row),
        "source": row.get("source"),
    }


def value_of(row: dict[str, Any]) -> Any:
    """Whichever typed column holds a daily row's value."""
    return next(
        (
            row[k]
            for k in ("value_num", "value_text", "value_bool")
            if row.get(k) is not None
        ),
        row.get("value_time") or row.get("value_json"),
    )


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


class OverwriteError(RuntimeError):
    """A write that would silently erase data."""


@mcp.tool()
async def add_to_counter(
    metric_key: str, amount: float = 1, date_key: str | None = None
) -> Any:
    """ADD to a day's count: water bottles, coffees, cigarettes, pees.

    Use it for "ajoute une bouteille / un café / une clope / un pipi": it
    adds ``amount`` to the day's total (default: the user's today) and
    never erases it. A negative amount takes back a wrong entry (never
    below 0). Returns the total before (``previous``) and after
    (``total``). Keys: water.bottles_1_5, habit.coffee, habit.cigarettes,
    habit.urges_broken, elimination.urination (a pee is logged now; for
    another time use log_urination).
    """
    body = {"metric": metric_key, "amount": amount}
    if date_key:
        body["date_key"] = date_key
    return await client.post("/sync/tally", body)


@mcp.tool()
async def record_measurement(
    metric_key: str,
    value: Any,
    date_key: str | None = None,
    replace: bool = False,
) -> Any:
    """SET a metric's value for a day (weight, sleep, a symptom…).

    It REPLACES the day's value: never use it to add to a count (use
    add_to_counter). When the day already holds a different value it
    refuses, unless ``replace`` is true — pass it only after the user
    confirmed the new value. Returns the value it replaced (``previous``).
    """
    day = today(date_key)
    previous = await _stored(metric_key, day)
    if previous is not None and not replace and not same(previous, value):
        raise OverwriteError(
            f"{metric_key} already holds {previous} on {day}; nothing was "
            "written. To add to a count use add_to_counter. To replace "
            "it, confirm the new value with the user, then call again "
            "with replace=true."
        )
    item = {"metric_key": metric_key, "date_key": day, "value": value}
    rows = await client.post("/measurements", {"items": [item]})
    return {"previous": previous, "recorded": rows}


async def _stored(metric_key: str, day: str) -> Any:
    """The value a metric already holds for ``day`` (None if empty)."""
    params = {"metric_key": metric_key, "start": day, "end": day}
    rows = await client.get("/measurements", params)
    daily = [row for row in rows if row.get("event_id") is None]
    return value_of(daily[0]) if daily else None


def same(stored_value: Any, value: Any) -> bool:
    """Whether a new value equals the stored one (5 == 5.0 == "5")."""
    try:
        return float(stored_value) == float(value)
    except (TypeError, ValueError):
        return str(stored_value) == str(value)


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
