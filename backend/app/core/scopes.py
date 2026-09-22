"""Canonical API-token scopes (least-privilege machine access)."""

from __future__ import annotations

INGEST_WATCH = "ingest:watch"
INGEST_PPC = "ingest:ppc"
INGEST_PHOTO = "ingest:photo"
WRITE_MEASUREMENTS = "write:measurements"
WRITE_METRICS = "write:metrics"
READ_ALL = "read:all"
#: Everything the web app does (e.g. for the MCP server), except managing
#: tokens, MFA and the account, which need an interactive login.
HUB_FULL = "hub:full"

#: Every scope a token may be granted.
ALL_SCOPES: frozenset[str] = frozenset(
    {
        INGEST_WATCH,
        INGEST_PPC,
        INGEST_PHOTO,
        WRITE_MEASUREMENTS,
        WRITE_METRICS,
        READ_ALL,
        HUB_FULL,
    }
)
