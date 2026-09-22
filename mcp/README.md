# Phoenix Health Hub — MCP server

Exposes **every feature of the hub** over the **Model Context Protocol**, so
an MCP client (Claude Desktop, OpenWebUI, the MCP Hub…) can read and act on
the whole record conversationally (§9). Every tool is a **client of the REST
API** — there is no parallel path to the database, so the MCP sees exactly
what the web pages show.

## Tools (53)

| Area | Tools |
|------|-------|
| Data (Apple Health, HAE, labs, entries) | `health_summary`, `list_domains`, `list_metrics`, `metric_overview`, `get_measurements`, `get_samples`, `get_trend`, `domain_dashboard`, `daily_summary`, `data_inventory`, `reconcile_data`, `record_measurement`, `delete_measurement`, `create_metric`, `update_metric`, `export_data` |
| Record (Dossier / Suivi) | `medical_record`, `care_overview`, `list_documents`, `document_text`, `analyze_document`, `analyze_all_documents`, `upload_document`, `delete_document`, `list_conditions`, `save_condition`, `delete_condition`, `list_treatments`, `save_treatment`, `delete_treatment`, `list_appointments`, `add_appointment`, `delete_appointment`, `clinical_observations` |
| Évolution, photos, Apple records | `metabolic_markers`, `evolution_trend`, `save_profile`, `list_photos`, `photo_analysis`, `analyze_photo`, `reanalyze_all_photos`, `list_workouts`, `list_ecg`, `list_routes`, `list_imports` |
| Reports, automations, anything else | `generate_report` (default: AI clinical synthesis), `list_reports`, `get_report`, `list_automations`, `create_automation`, `run_automation`, `api_get`, `api_call` |

`api_get` / `api_call` reach any route not covered by a tool (see
`/api/v1/openapi.json`). `document_text` returns what the AI read from a
document, to check an extraction against its source.

## Configuration

| Variable | Purpose |
|----------|---------|
| `API_BASE_URL` | REST API base (default `http://api:8000/api/v1`). |
| `PHOENIX_API_TOKEN` | API token with the **`hub:full`** scope (web app › Import › « Jetons d’accès (API) » › « Accès complet — MCP / assistant »). It can do everything the web app does **except** managing tokens, 2FA and the account. |
| `MCP_AUTH_TOKEN` | **Required** for `sse` / `streamable-http`: every client request must send `Authorization: Bearer <MCP_AUTH_TOKEN>` (401 otherwise). Generate with `openssl rand -hex 32`. |
| `MCP_TRANSPORT` | `sse` (default), `streamable-http` or `stdio`. |
| `MCP_HOST` / `MCP_PORT` | Bind address inside the container (default `0.0.0.0:9000`). |
| `MCP_BIND` | Host interface the compose port is published on (default `127.0.0.1`; `0.0.0.0` for the LAN). |

The server holds a key to the whole medical record: keep it on the
machine or the LAN (VPN / authenticated reverse proxy for remote access),
never open it to the Internet.

## Run

```bash
docker compose --profile mcp up -d mcp   # in the repo root
# or locally:
uv pip install -e ".[dev]" && python -m phoenix_mcp.server
```

Client example (SSE): URL `http://<host>:9000/sse`, header
`Authorization: Bearer <MCP_AUTH_TOKEN>`. For a desktop client that launches
the server itself, use `MCP_TRANSPORT=stdio` (no network, no secret needed).

## Develop

```bash
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check phoenix_mcp tests && mypy phoenix_mcp && pytest
```
