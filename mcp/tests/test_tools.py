"""MCP client + tool-helper tests (no network, via MockTransport)."""

from __future__ import annotations

import httpx

from phoenix_mcp import client, server


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/metrics"):
        return httpx.Response(200, json=[{"key": "body.weight"}])
    return httpx.Response(404, json={"detail": "not found"})


async def test_get_returns_json_over_transport() -> None:
    client.configure("http://test/api/v1", "tok", httpx.MockTransport(_handler))
    data = await client.get("/metrics")
    assert data[0]["key"] == "body.weight"


def test_summarize_groups_by_metric() -> None:
    rows = [
        {"metric_id": "m1", "value": 5},
        {"metric_id": "m2", "value": "x"},
    ]
    summary = server._summarize("2026-01-01", rows)
    assert summary["count"] == 2
    assert summary["values"]["m1"] == 5


def test_today_defaults() -> None:
    assert server._today("2026-01-02") == "2026-01-02"
    assert len(server._today(None)) == 10
