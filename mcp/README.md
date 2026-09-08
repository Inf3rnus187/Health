# MCP server (Phase 7 — placeholder)

The MCP server exposes the hub's tools (`list_metrics`, `record_measurement`,
`get_trend`, `generate_report`, …) to an MCP client such as OpenWebUI. It is a
**client of the REST API** (`API_BASE_URL`) so there is a single source of
truth — it never talks to the database directly (§9).

This directory currently contains a placeholder service so the Docker profile
builds and runs. The tool implementations land in Phase 7.

Enable it with:

```bash
docker compose --profile mcp up -d mcp
```
