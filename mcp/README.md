# Phoenix Health Hub — MCP server

Exposes **every feature of the hub** over the **Model Context Protocol**, so
an MCP client (Claude Desktop, OpenWebUI, the MCP Hub…) can read and act on
the whole record conversationally (§9). Every tool is a **client of the REST
API** — there is no parallel path to the database, so the MCP sees exactly
what the web pages show.

## Tools (81)

| Area | Tools |
|------|-------|
| Data (Apple Health, HAE, labs, entries) | `health_summary`, `list_domains`, `list_metrics`, `metric_overview`, `get_measurements`, `get_samples`, `get_trend`, `domain_dashboard`, `daily_summary`, `data_inventory`, `reconcile_data`, `add_to_counter`, `record_measurement`, `delete_measurement`, `create_metric`, `update_metric`, `export_data` |
| Record (Dossier / Suivi) | `medical_record`, `care_overview`, `list_documents`, `document_text`, `analyze_document`, `analyze_all_documents`, `upload_document`, `delete_document`, `list_conditions`, `save_condition`, `delete_condition`, `list_treatments`, `save_treatment`, `delete_treatment`, `list_appointments`, `add_appointment`, `delete_appointment`, `clinical_observations` |
| Journal (pee, meals) | `log_urination`, `list_urinations`, `delete_urination`, `log_meal`, `list_meals`, `get_meal`, `update_meal`, `analyze_meal`, `delete_meal` |
| Work hours | `clock_in`, `clock_out`, `work_sessions`, `save_work_session`, `delete_work_session`, `work_stats`, `import_work_log`, `export_work` (PDF: `generate_report("work")`) |
| Work ↔ health file | `import_logs`, `list_absences`, `save_absence`, `delete_absence`, `list_evidence`, `add_evidence`, `delete_evidence`, `sleep_nights`, `add_sleep_night`, `work_health` (PDF: `generate_report("work_health")`) |
| Évolution, photos, Apple records | `metabolic_markers`, `evolution_trend`, `save_profile`, `list_photos`, `photo_analysis`, `analyze_photo`, `reanalyze_all_photos`, `list_workouts`, `list_ecg`, `list_routes`, `list_imports` |
| Reports, automations, anything else | `generate_report` (default: AI clinical synthesis), `list_reports`, `get_report`, `list_automations`, `create_automation`, `run_automation`, `api_get`, `api_call` |

`api_get` / `api_call` reach any route not covered by a tool (see
`/api/v1/openapi.json`). `document_text` returns what the AI read from a
document, to check an extraction against its source.

## Configuration

| Variable | Purpose |
|----------|---------|
| `API_BASE_URL` | REST API base (default `http://api:8000/api/v1`). |
| `PHOENIX_API_TOKEN` | Only for `stdio` (no HTTP header to carry a token). |
| `MCP_TRANSPORT` | `streamable-http` (default in compose: one request, one JSON answer — a plain `curl` works), `sse` or `stdio`. |
| `MCP_HOST` / `MCP_PORT` | Bind address inside the container (default `0.0.0.0:9000`). |
| `MCP_BIND` | Host interface the compose port is published on (default `127.0.0.1`; `0.0.0.0` for the LAN). |

**Authentication: one token.** Each client sends its own API token with the
**`hub:full`** scope (web app › Import › « Jetons d’accès (API) » ›
« Accès complet — MCP / assistant ») as `Authorization: Bearer <token>`.
The server checks it with the API (401 unknown or revoked, 403 not
`hub:full`) and calls the API with it: nothing secret in `.env`, each
user sees their own data, revoking the token cuts the access. Keep the
port on the machine or the LAN (VPN for remote access), never on the
Internet.

## Run

```bash
docker compose --profile mcp up -d mcp   # in the repo root
# or locally:
uv pip install -e ".[dev]" && python -m phoenix_mcp.server
```

Client example: URL `http://<host>:9000/mcp` (or `/sse` in sse mode), header
`Authorization: Bearer <hub:full API token>`. For a desktop client that
launches the server itself, use `MCP_TRANSPORT=stdio` with
`PHOENIX_API_TOKEN`.
Step-by-step setup (Claude Desktop, Claude Code, stdio over SSH):
[docs/guides/mcp.md](../docs/guides/mcp.md). Every tool with its parameters:
[docs/mcp-tools.md](../docs/mcp-tools.md) — regenerate with
`python -m phoenix_mcp.doc > ../docs/mcp-tools.md` after changing a tool.

## Develop

```bash
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check phoenix_mcp tests && mypy phoenix_mcp && pytest
```
