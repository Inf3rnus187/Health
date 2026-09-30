"""HTTP middleware attaching baseline security response headers.

The strict Content-Security-Policy is applied by the web tier (Nginx),
which serves HTML; the API returns JSON and sets the transport-agnostic
headers here (§12.1).
"""

from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",
}


class SecurityHeadersMiddleware:
    """Attach baseline security headers to every response.

    Plain ASGI: it adds the headers to the answer's first message and
    lets the body through untouched (``BaseHTTPMiddleware`` copied every
    answer through a stream: 60 ms for a 580 KB dashboard,
    docs/performance.md). A header the route set itself is kept.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the application."""
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Add the security headers to the downstream response."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def sending(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in _HEADERS.items():
                    headers.setdefault(key, value)
            await send(message)

        await self.app(scope, receive, sending)
