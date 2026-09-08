# Phoenix Health Hub — MCP server

Exposes the hub's tools over the **Model Context Protocol** so an MCP client
(OpenWebUI, the MCP Hub, …) can drive the app conversationally (§9). Every
tool is a **client of the REST API** — there is no parallel path to the
database, so there is a single source of truth.

## Tools

`list_metrics`, `create_metric`, `record_measurement`, `get_measurements`,
`get_trend`, `get_daily_summary`, `get_photo_analysis`, `compare_photos`,
`generate_report`, `export_data`.

## Configuration

| Variable | Purpose |
|----------|---------|
| `API_BASE_URL` | REST API base (default `http://api:8000/api/v1`). |
| `PHOENIX_API_TOKEN` | Scoped API token used to authenticate. |
| `MCP_TRANSPORT` | `sse` (default), `streamable-http` or `stdio`. |
| `MCP_HOST` / `MCP_PORT` | Bind address (default `0.0.0.0:9000`). |

Create a scoped token with `POST /api/v1/tokens` (e.g. scopes `read:all`,
`write:measurements`) and set it as `PHOENIX_API_TOKEN` in `.env`.

## Run

```bash
docker compose --profile mcp up -d mcp   # in the repo root
# or locally:
uv pip install -e ".[dev]" && python -m phoenix_mcp.server
```

## Develop

```bash
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check phoenix_mcp tests && mypy phoenix_mcp && pytest
```
