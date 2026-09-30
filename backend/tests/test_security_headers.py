"""Every API answer carries the baseline security headers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "x-xss-protection": "0",
}


@pytest.mark.parametrize(
    "path", ["/health", "/api/v1/measurements", "/api/v1/nowhere"]
)
async def test_each_answer_has_the_headers_once(
    client: AsyncClient, auth: dict[str, str], path: str
) -> None:
    got = await client.get(path, headers=auth)
    for name, value in HEADERS.items():
        assert got.headers.get_list(name) == [value], (path, name)


async def test_an_error_has_them_too(client: AsyncClient) -> None:
    got = await client.get("/api/v1/measurements")  # no session: 401
    assert got.status_code == 401
    assert got.headers["x-frame-options"] == "DENY"
