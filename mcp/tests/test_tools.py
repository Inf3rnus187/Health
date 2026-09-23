"""MCP client, tools and access gate (no network: MockTransport / ASGI)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from starlette.types import Receive, Scope, Send

from phoenix_mcp import (
    auth,
    client,
    server,  # noqa: F401 - importing registers every tool
    tools_data,
    tools_journal,
    tools_record,
    tools_reports,
    tools_work,
    tools_workfile,
)
from phoenix_mcp.app import mcp

Seen = list[httpx.Request]


def _capture(status: int = 200, payload: Any = None) -> Seen:
    """Route every call to a recorder answering ``payload``."""
    seen: Seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = {"ok": 1} if payload is None else payload
        return httpx.Response(status, json=body)

    client.configure("http://test/api/v1", "tok", httpx.MockTransport(handler))
    return seen


async def test_every_area_of_the_hub_has_tools() -> None:
    names = {tool.name for tool in await mcp.list_tools()}
    expected = {
        "health_summary",
        "metric_overview",
        "data_inventory",
        "reconcile_data",
        "medical_record",
        "care_overview",
        "document_text",
        "analyze_all_documents",
        "save_condition",
        "save_treatment",
        "metabolic_markers",
        "evolution_trend",
        "generate_report",
        "get_report",
        "api_get",
        "api_call",
    }
    assert expected <= names
    assert len(names) >= 50


async def test_requests_carry_the_token_and_drop_unset_params() -> None:
    seen = _capture()
    await tools_data.get_measurements("body.weight", start="2026-01-01")
    request = seen[0]
    assert request.headers["authorization"] == "Bearer tok"
    assert request.url.path == "/api/v1/measurements"
    assert dict(request.url.params) == {
        "metric_key": "body.weight",
        "start": "2026-01-01",
    }


async def test_daily_summary_filters_one_day() -> None:
    seen = _capture(payload=[])
    await tools_data.daily_summary("2026-09-16")
    params = dict(seen[0].url.params)
    assert params == {"start": "2026-09-16", "end": "2026-09-16"}


def test_daily_values_carry_their_metric_name() -> None:
    row = {"metric_id": "m1", "value_num": 4.0, "source": "manual"}
    metrics = {"m1": {"key": "habit.cigarettes", "label": "Cigarettes"}}
    named = tools_data.named(row, metrics)
    assert named["key"] == "habit.cigarettes"
    assert named["value"] == 4.0


def _day_holds(value: float | None) -> Seen:
    """GET /measurements answers ``value`` (none if None); POST echoes."""
    seen: Seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "GET":
            rows = [] if value is None else [_row(value)]
            return httpx.Response(200, json=rows)
        return httpx.Response(201, json=[{"ok": 1}])

    client.configure("http://test/api/v1", "tok", httpx.MockTransport(handler))
    return seen


def _row(value: float) -> dict[str, Any]:
    return {"metric_id": "m1", "event_id": None, "value_num": value}


async def test_counts_are_added_never_replaced() -> None:
    seen = _capture(payload={"previous": 7.0, "total": 8.0})
    result = await tools_data.add_to_counter("habit.cigarettes")
    request = seen[0]
    assert (request.method, request.url.path) == ("POST", "/api/v1/sync/tally")
    body = json.loads(request.content)
    assert body == {"metric": "habit.cigarettes", "amount": 1}
    assert result["total"] == 8.0


async def test_record_refuses_to_erase_a_value() -> None:
    seen = _day_holds(7.0)
    with pytest.raises(tools_data.OverwriteError, match="already holds 7.0"):
        await tools_data.record_measurement("habit.cigarettes", 1, "2026-09-20")
    assert [r.method for r in seen] == ["GET"]


async def test_record_replaces_once_confirmed() -> None:
    seen = _day_holds(7.0)
    result = await tools_data.record_measurement(
        "habit.cigarettes", 9, "2026-09-20", replace=True
    )
    assert [r.method for r in seen] == ["GET", "POST"]
    assert result["previous"] == 7.0


async def test_record_writes_an_empty_or_equal_day() -> None:
    for held, value in ((None, 72.4), (5.0, "5")):
        seen = _day_holds(held)
        await tools_data.record_measurement("body.weight", value, "2026-09-20")
        assert [r.method for r in seen] == ["GET", "POST"]


async def test_save_condition_creates_or_replaces() -> None:
    seen = _capture()
    await tools_record.save_condition("Asthme")
    await tools_record.save_condition("Asthme", condition_id="c1")
    assert [(r.method, r.url.path) for r in seen] == [
        ("POST", "/api/v1/conditions"),
        ("PUT", "/api/v1/conditions/c1"),
    ]
    assert json.loads(seen[1].content)["status"] == "active"


async def test_default_report_is_the_ai_synthesis() -> None:
    seen = _capture()
    await tools_reports.generate_report()
    assert json.loads(seen[0].content)["type"] == "synthesis"


async def test_api_errors_carry_the_api_message() -> None:
    _capture(403, {"detail": "User session required"})
    with pytest.raises(client.ApiError, match="403: User session required"):
        await tools_record.medical_record()


async def test_upload_sends_a_multipart_form() -> None:
    seen = _capture()
    await tools_record.upload_document("fs.pdf", "JVBERi0=", kind="imagerie")
    body = seen[0].content
    assert b'name="kind"' in body and b"imagerie" in body
    assert b"%PDF-" in body


Seen_tokens = list[str | None]


def _api(seen: Seen_tokens) -> None:
    """A fake API answering /auth/scopes per token."""

    def handler(request: httpx.Request) -> httpx.Response:
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        seen.append(token)
        if token == "full":
            return httpx.Response(200, json={"full_access": True})
        if token == "ingest":
            return httpx.Response(200, json={"full_access": False})
        return httpx.Response(401, json={"detail": "Invalid credentials"})

    client.configure("http://test/api/v1", "", httpx.MockTransport(handler))
    auth._verified.clear()


def _app(used: Seen_tokens) -> Any:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        used.append(client.REQUEST_TOKEN.get())
        start = {"type": "http.response.start", "status": 200, "headers": []}
        await send(start)
        await send({"type": "http.response.body", "body": b"ok"})

    return app


async def _get(app: Any, token: str | None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as h:
        return (await h.get("/mcp", headers=headers)).status_code


async def test_the_callers_hub_token_is_checked_and_used() -> None:
    api_calls: Seen_tokens = []
    used: Seen_tokens = []
    _api(api_calls)
    gated = auth.bearer_gate(_app(used))
    assert await _get(gated, None) == 401
    assert await _get(gated, "revoked") == 401
    assert await _get(gated, "ingest") == 403
    assert await _get(gated, "full") == 200
    assert await _get(gated, "full") == 200  # cached: no second API check
    assert used == ["full", "full"]
    assert api_calls.count("full") == 1
    assert client.REQUEST_TOKEN.get() is None  # reset after the request


async def test_a_meal_is_sent_as_a_form_with_its_photo() -> None:
    seen = _capture()
    await tools_journal.log_meal("salade, poulet", photo_base64="SGVsbG8=")
    body = seen[0].content
    assert seen[0].url.path == "/api/v1/meals"
    assert b"salade, poulet" in body and b'filename="repas.jpg"' in body


async def test_work_clock_and_dry_run_import() -> None:
    seen = _capture()
    await tools_work.clock_in()
    await tools_work.clock_out("2026-03-02T17:30")
    bodies = [json.loads(r.content) for r in seen]
    assert bodies == [
        {"kind": "in", "at": None},
        {"kind": "out", "at": "2026-03-02T17:30"},
    ]
    await tools_work.import_work_log("02/03/2026;08:00;17:00")
    upload = seen[-1]
    assert upload.url.path == "/api/v1/work/import"
    assert dict(upload.url.params) == {"dry_run": "true"}
    assert b"02/03/2026;08:00;17:00" in upload.content


async def test_shortcut_logs_are_sent_together() -> None:
    seen = _capture()
    await tools_workfile.import_logs(
        [
            {"filename": "Embauche.txt", "text": "1 | 02/03/2026 08:10"},
            {"filename": "Debauche.txt", "text": "1 | 02/03/2026 17:00"},
        ]
    )
    upload = seen[0]
    assert upload.url.path == "/api/v1/logs/import"
    assert upload.content.count(b'name="files"') == 2
