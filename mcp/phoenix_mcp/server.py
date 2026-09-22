"""Phoenix Health Hub MCP server: every hub feature over MCP (§9).

Each tool is a thin wrapper over the REST API (single source of truth):
data and metrics, the medical record (Dossier / Suivi), documents and
their text, markers, weight and photo evolution, reports with the AI
clinical synthesis, automations, plus ``api_get`` / ``api_call`` for any
other route. Configure ``API_BASE_URL`` and ``PHOENIX_API_TOKEN`` (a
``hub:full`` token); network transports also need ``MCP_AUTH_TOKEN``.
Run with ``python -m phoenix_mcp.server`` (``MCP_TRANSPORT``: sse,
streamable-http or stdio).
"""

from __future__ import annotations

import os

import uvicorn

from phoenix_mcp import (  # noqa: F401 - importing registers the tools
    tools_body,
    tools_data,
    tools_record,
    tools_reports,
)
from phoenix_mcp.app import mcp
from phoenix_mcp.auth import bearer_gate

_NETWORK = {"sse", "streamable-http"}


def main() -> None:
    """Run the MCP server with the configured transport."""
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    if transport not in _NETWORK:
        mcp.run(transport="stdio")
        return
    secret = os.environ.get("MCP_AUTH_TOKEN", "")
    if not secret:
        raise SystemExit(
            "MCP_AUTH_TOKEN is required for the sse / streamable-http "
            "transports (the server can read the whole medical record)."
        )
    app = mcp.sse_app() if transport == "sse" else mcp.streamable_http_app()
    uvicorn.run(
        bearer_gate(app, secret),
        host=mcp.settings.host,
        port=mcp.settings.port,
    )


if __name__ == "__main__":
    main()
