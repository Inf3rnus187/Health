"""HTTP client wrapping the Phoenix REST API for the MCP tools.

The MCP server is a *client of the API* — never a parallel path to the
database (§9). It authenticates with an API token; a ``hub:full`` token
lets it do everything the web app does (except managing tokens, MFA and
the account). API errors are raised with the API's own message.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_BASE = os.environ.get("API_BASE_URL", "http://api:8000/api/v1")
_TOKEN = os.environ.get("PHOENIX_API_TOKEN", "")
_TRANSPORT: httpx.AsyncBaseTransport | None = None
_TIMEOUT = 120.0
#: A synthesis report without a worker runs the text model inline.
LONG = 1200.0


class ApiError(RuntimeError):
    """The API refused a call (status and its detail message)."""


def configure(
    base: str,
    token: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    """Override base URL/token/transport (used by tests)."""
    global _BASE, _TOKEN, _TRANSPORT
    _BASE, _TOKEN, _TRANSPORT = base, token, transport


async def request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: Any = None,
    timeout: float = _TIMEOUT,
) -> Any:
    """Call the API; return its JSON (or text) body."""
    async with _new_client(timeout) as client:
        response = await client.request(
            method, path, params=_clean(params), json=body
        )
    return _body(method, path, response)


async def upload(path: str, files: dict[str, Any], data: dict[str, str]) -> Any:
    """POST a multipart form (a document, a lab PDF…)."""
    async with _new_client(_TIMEOUT, json=False) as client:
        response = await client.post(path, files=files, data=_clean(data))
    return _body("POST", path, response)


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET ``path`` and return the parsed body."""
    return await request("GET", path, params=params)


async def post(path: str, body: Any = None) -> Any:
    """POST ``body`` to ``path`` and return the parsed body."""
    return await request("POST", path, body=body)


def _new_client(timeout: float, *, json: bool = True) -> httpx.AsyncClient:
    """An async HTTP client with the token."""
    headers = {"Content-Type": "application/json"} if json else {}
    if _TOKEN:
        headers["Authorization"] = f"Bearer {_TOKEN}"
    return httpx.AsyncClient(
        base_url=_BASE, headers=headers, transport=_TRANSPORT, timeout=timeout
    )


def _clean(params: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop unset (None) parameters."""
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _body(method: str, path: str, response: httpx.Response) -> Any:
    """The response body, or an ApiError with the API's message."""
    if response.is_error:
        raise ApiError(
            f"{method} {path} -> {response.status_code}: {_detail(response)}"
        )
    if not response.content:
        return None
    if "json" in response.headers.get("content-type", ""):
        return response.json()
    return response.text


def _detail(response: httpx.Response) -> str:
    """The API's error message (``detail``) or the raw text."""
    try:
        return str(response.json().get("detail", response.text))
    except ValueError:
        return response.text[:300]
