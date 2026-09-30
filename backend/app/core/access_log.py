"""One access-log line per API request: when, who, what, status, how long.

``2026-09-30 05:37:56 +0000 192.168.1.250 "GET /api/v1/meals HTTP/1.0"
200 45 ms`` — the time in UTC like nginx's log, the client nginx saw
(``X-Real-IP``), and the time the API took. A request of a second or
more ends with ``slow``, easy to find (``docker compose logs api | grep
slow``). A token in the URL (``?token=…``) is written ``token=***``.
Replaces uvicorn's own access line, which had no time.
"""

from __future__ import annotations

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings

LOGGER = "app.access"
_SLOW_MS = get_settings().log_slow_ms
_log = logging.getLogger(LOGGER)


class AccessLog:
    """ASGI middleware writing the access line once the answer is sent."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the application."""
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Time the request and log it (also when it fails)."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start, status = time.perf_counter(), [500]

        async def sending(message: Message) -> None:
            if message["type"] == "http.response.start":
                status[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, sending)
        finally:
            ms = (time.perf_counter() - start) * 1000
            _log.info(line(scope, status[0], ms))


def line(scope: Scope, status: int, ms: float) -> str:
    """``client "METHOD /path?query HTTP/x" status N ms [slow]``."""
    from app.core.logging import redact

    query = scope.get("query_string", b"").decode("latin-1")
    target = scope.get("path", "") + (f"?{query}" if query else "")
    version = scope.get("http_version")
    request = f'{scope.get("method")} {redact(target)} HTTP/{version}'
    slow = " slow" if ms >= _SLOW_MS else ""
    return f'{_client(scope)} "{request}" {status} {ms:.0f} ms{slow}'


def _client(scope: Scope) -> str:
    """The address nginx saw (X-Real-IP), else the connection's."""
    for name, value in scope.get("headers", []):
        if name == b"x-real-ip":
            return str(value.decode("latin-1"))
    client = scope.get("client")
    return str(client[0]) if client else "-"
