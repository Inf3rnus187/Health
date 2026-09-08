"""Placeholder MCP service (Phase 7).

Keeps the container alive so the ``mcp`` compose profile is runnable.
The real server will expose the hub's tools as an MCP client of the REST
API at ``API_BASE_URL``.
"""

from __future__ import annotations

import os
import time


def main() -> None:
    """Log intent and idle until the container is stopped."""
    api = os.environ.get("API_BASE_URL", "http://api:8000/api/v1")
    print(f"[mcp] placeholder started; API base = {api}", flush=True)
    print("[mcp] tools will be implemented in Phase 7.", flush=True)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
