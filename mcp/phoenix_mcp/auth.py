"""Gate for the network transports: the caller's own API token.

Every request must carry ``Authorization: Bearer <token>`` where the token
is a ``hub:full`` API token created in the web app (Import › Jetons
d'accès). The gate asks the API what the token may do (answer cached for
a minute), rejects anything else (401 unknown / revoked, 403 not
``hub:full``) and hands the token to the tools, which call the API with
it. Revoking the token in the web app cuts the access.
"""

from __future__ import annotations

import hashlib
import time

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from phoenix_mcp import client

_TTL = 60.0  # seconds a verified token is trusted before re-checking
_verified: dict[str, float] = {}


def bearer_gate(app: ASGIApp) -> ASGIApp:
    """Wrap ``app``: only requests with a hub:full API token get through."""

    async def gated(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        token = bearer(scope)
        status = await check(token) if token else 401
        if status != 200:
            await _deny(status, scope, receive, send)
            return
        reset = client.REQUEST_TOKEN.set(token)
        try:
            await app(scope, receive, send)
        finally:
            client.REQUEST_TOKEN.reset(reset)

    return gated


def bearer(scope: Scope) -> str | None:
    """The bearer token of a request, if any."""
    headers = dict(scope.get("headers") or [])
    value: bytes = headers.get(b"authorization", b"")
    kind, _, token = value.decode("latin-1").partition(" ")
    if kind.lower() != "bearer":
        return None
    return token.strip() or None


async def check(token: str) -> int:
    """200 for a hub:full token, else the HTTP status to answer."""
    key = hashlib.sha256(token.encode()).hexdigest()
    if _verified.get(key, 0.0) > time.monotonic():
        return 200
    reset = client.REQUEST_TOKEN.set(token)
    try:
        info = await client.get("/auth/scopes")
    except client.ApiError as exc:
        return 401 if "-> 401" in str(exc) else 502
    finally:
        client.REQUEST_TOKEN.reset(reset)
    if not info.get("full_access"):
        return 403
    _verified[key] = time.monotonic() + _TTL
    return 200


async def _deny(
    status: int, scope: Scope, receive: Receive, send: Send
) -> None:
    """Answer a refused request with a short explanation."""
    text = {
        401: "Unauthorized: send Authorization: Bearer <API token hub:full>",
        403: "Forbidden: the token needs the hub:full scope",
        502: "API unreachable",
    }[status]
    denied = PlainTextResponse(
        text, status_code=status, headers={"WWW-Authenticate": "Bearer"}
    )
    await denied(scope, receive, send)
