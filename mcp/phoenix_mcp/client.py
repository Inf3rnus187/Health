"""HTTP client wrapping the Phoenix REST API for the MCP tools.

The MCP server is a *client of the API* — never a parallel path to the
database (§9). Auth uses a scoped API token.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_BASE = os.environ.get("API_BASE_URL", "http://api:8000/api/v1")
_TOKEN = os.environ.get("PHOENIX_API_TOKEN", "")
_TRANSPORT: httpx.AsyncBaseTransport | None = None


def configure(
    base: str,
    token: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    """Override base URL/token/transport (used by tests)."""
    global _BASE, _TOKEN, _TRANSPORT
    _BASE, _TOKEN, _TRANSPORT = base, token, transport


def _new_client() -> httpx.AsyncClient:
    """Build an configured async HTTP client."""
    headers = {"Content-Type": "application/json"}
    if _TOKEN:
        headers["Authorization"] = f"Bearer {_TOKEN}"
    return httpx.AsyncClient(
        base_url=_BASE,
        headers=headers,
        transport=_TRANSPORT,
        timeout=60.0,
    )


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET ``path`` and return the parsed JSON body."""
    async with _new_client() as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()


async def post(path: str, payload: dict[str, Any] | None = None) -> Any:
    """POST ``payload`` to ``path`` and return the parsed JSON body."""
    async with _new_client() as client:
        response = await client.post(path, json=payload)
        response.raise_for_status()
        return response.json()


async def get_text(path: str, params: dict[str, Any] | None = None) -> str:
    """GET ``path`` and return the raw text body (for exports)."""
    async with _new_client() as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.text
