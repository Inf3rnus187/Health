"""Halves never paired: completing absorbs them, or merge two sessions."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

WORK = "/api/v1/work"
DAY = {"start": "2026-03-02", "end": "2026-03-02"}


async def _halves(client: AsyncClient, auth: dict[str, str]) -> tuple[Any, Any]:
    """A lone clock-out at 19:12 logged first, then a lone clock-in 09:02."""
    out = await client.post(
        f"{WORK}/clock", json={"kind": "out", "at": "2026-03-02T19:12"},
        headers=auth,
    )  # fmt: skip
    came = await client.post(
        f"{WORK}/clock", json={"kind": "in", "at": "2026-03-02T09:02"},
        headers=auth,
    )  # fmt: skip
    return came.json(), out.json()


async def _sessions(client: AsyncClient, auth: dict[str, str]) -> Any:
    got = await client.get(f"{WORK}/sessions", params=DAY, headers=auth)
    return got.json()


async def test_completing_takes_in_the_lone_clock_in(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    came, out = await _halves(client, auth)
    todo = (await client.get(f"{WORK}/incomplete", headers=auth)).json()
    card = next(t for t in todo if t["id"] == out["id"])
    (other,) = card["context"]["others"]
    assert (other["id"], other["start"], other["end"]) == (
        came["id"], "09:02", None,
    )  # fmt: skip
    assert other["merged"] == "09:02 → 19:12"
    done = await client.put(
        f"{WORK}/sessions/{out['id']}",
        json={"start_at": "2026-03-02T08:55"},
        headers=auth,
    )
    assert done.status_code == 200, done.text
    (row,) = await _sessions(client, auth)
    assert (row["hours"], row["status"]) == (10.28, "complete")
    assert "embauche seule de 09:02 réunie" in row["note"]
    assert (await client.get(f"{WORK}/incomplete", headers=auth)).json() == []


async def test_two_halves_merge_into_one_session(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    came, out = await _halves(client, auth)
    merged = await client.post(
        f"{WORK}/sessions/{out['id']}/merge",
        json={"other_id": came["id"]},
        headers=auth,
    )
    assert merged.status_code == 200, merged.text
    body = merged.json()
    assert (body["hours"], body["source"]) == (10.17, "edited")
    assert "réunie avec 09:02 → ?" in body["note"]
    assert [r["id"] for r in await _sessions(client, auth)] == [out["id"]]


async def test_an_overlap_names_the_session_and_leaves_room_after_it(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await client.post(
        f"{WORK}/sessions",
        json={"start_at": "2026-03-02T09:02", "end_at": "2026-03-02T12:30"},
        headers=auth,
    )
    out = (await client.post(
        f"{WORK}/clock", json={"kind": "out", "at": "2026-03-02T19:12"},
        headers=auth,
    )).json()  # fmt: skip
    refused = await client.put(
        f"{WORK}/sessions/{out['id']}",
        json={"start_at": "2026-03-02T09:00"},
        headers=auth,
    )
    assert refused.status_code == 422
    assert refused.json()["detail"].startswith(
        "Chevauche la session du 02/03/2026 09:02 → 12:30 :"
    )
    (card,) = (await client.get(f"{WORK}/incomplete", headers=auth)).json()
    (other,) = card["context"]["others"]
    assert other["free"].startswith("2026-03-02T12:30")
    assert other["merged"] == "09:02 → 19:12"
    remote = await client.post(
        f"{WORK}/sessions",
        json={"start_at": "2026-03-02T21:00", "end_at": "2026-03-02T22:00",
              "place": "remote"},
        headers=auth,
    )  # fmt: skip
    mixed = await client.post(
        f"{WORK}/sessions/{out['id']}/merge",
        json={"other_id": remote.json()["id"]},
        headers=auth,
    )
    assert mixed.status_code == 422
