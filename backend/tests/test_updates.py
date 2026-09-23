"""The update notice: what ./update.sh wrote, and the request it runs."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from app.core.config import get_settings
from httpx import AsyncClient

URL = "/api/v1/system/update"


@pytest.fixture
def shared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "update_dir", str(tmp_path))
    return tmp_path


async def test_nothing_known_until_the_host_script_ran(
    client: AsyncClient, auth: dict[str, str], shared: Path
) -> None:
    body = (await client.get(URL, headers=auth)).json()
    assert (body["known"], body["behind"], body["watcher"]) == (False, 0, False)
    refused = await client.post(URL, headers=auth)
    assert refused.status_code == 409
    assert "./update.sh" in refused.json()["detail"]
    assert not (shared / "update-request").exists()


async def test_what_waits_and_a_request_for_the_host(
    client: AsyncClient, auth: dict[str, str], shared: Path
) -> None:
    (shared / "update.json").write_text(json.dumps({
        "behind": 2, "commits": ["dea1ec5 Tidy the page", "05aec03 Fix"],
        "areas": ["api", "web"], "checked_at": "2026-09-23T19:52:44Z",
        "current": "77fe6fa", "latest": "dea1ec5",
    }))  # fmt: skip
    (shared / "heartbeat").write_text(f"{int(time.time())}\n")
    body = (await client.get(URL, headers=auth)).json()
    assert (body["behind"], body["watcher"], body["state"]) == (2, True, "idle")
    assert body["rebuild"] == ["API et worker", "interface web"]
    asked = await client.post(URL, headers=auth)
    assert asked.json()["state"] == "requested"
    assert (shared / "update-request").read_text().strip()
    (shared / "update-request").unlink()  # the host took it
    (shared / "status.json").write_text(json.dumps({
        "state": "done", "message": "À jour (dea1ec5)", "commit": "dea1ec5",
    }))  # fmt: skip
    body = (await client.get(URL, headers=auth)).json()
    assert (body["state"], body["message"]) == ("done", "À jour (dea1ec5)")


async def test_a_stale_heartbeat_means_no_install_button(
    client: AsyncClient, auth: dict[str, str], shared: Path
) -> None:
    (shared / "heartbeat").write_text(f"{int(time.time()) - 3600}\n")
    assert (await client.get(URL, headers=auth)).json()["watcher"] is False
