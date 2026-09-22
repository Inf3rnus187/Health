"""Shared-secret gate for the network transports (SSE, streamable HTTP).

A ``hub:full`` API token lets the server read the whole medical record,
so over the network every request must carry
``Authorization: Bearer <MCP_AUTH_TOKEN>``. stdio needs no gate: it is
only reachable by the process that launched it.
"""

from __future__ import annotations

import hmac

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def bearer_gate(app: ASGIApp, secret: str) -> ASGIApp:
    """Wrap ``app``: HTTP requests without the secret get a 401."""
    if not secret:
        raise ValueError("MCP_AUTH_TOKEN is empty")
    expected = f"Bearer {secret}".encode()

    async def gated(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not allowed(scope, expected):
            denied = PlainTextResponse(
                "Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await denied(scope, receive, send)
            return
        await app(scope, receive, send)

    return gated


def allowed(scope: Scope, expected: bytes) -> bool:
    """Constant-time comparison of the Authorization header."""
    headers = dict(scope.get("headers") or [])
    given: bytes = headers.get(b"authorization", b"")
    return hmac.compare_digest(given, expected)
