# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **iPhone CSV sync**: the Apple Health import (`POST /imports/apple-health`)
  now **auto-detects** and ingests a **SimpleHealthExportCSV** zip (one CSV
  per HealthKit type) in addition to Apple's native `export.xml` — same
  full-fidelity `health_samples` storage, daily roll-ups and on-the-fly
  `apple.*` metric creation. This is the reliable device path since iOS
  refuses to import unsigned shortcut files (server-side signing is
  impossible). The Import → « Synchro iPhone » card now mints a
  `write:measurements` upload token and shows the exact POST config for the
  shortcut's upload step. The upload also accepts the token as a `?token=`
  query param (not just the `Authorization` header), so the shortcut needs
  only a URL — no fragile header entry on mobile. The CSV parser tolerates
  the real export's quirks (Excel `sep=,` preamble, UTF-8 BOM, CRLF), maps
  the short sleep-stage values (`asleepCore`/`asleepREM`/…) into the sleep
  roll-ups, and routes `HKWorkoutActivityType…` CSVs into the workouts
  table (duration/energy/distance) rather than generic `apple.*` samples.

- **iPhone one-tap sync**: Import → « Synchro iPhone » now offers a
  **pre-filled downloadable Shortcut** (`GET /sync/shortcut`) with the
  scoped token and endpoint already embedded — no data picking, no JSON
  editing. It posts to `POST /sync/health`, a Shortcut-friendly flat
  `{date_key?, metrics:{type:value}}` map with lenient numeric parsing
  (`"86,2 kg"`, `"8 542 pas"`). The manual copy/paste recipe and its dead
  helper components were removed.

### Changed

- **Robust ingestion**: a `healthkit_type` with no user mapping now
  resolves via the Apple spec and **auto-creates** its metric
  (`MetricCache`), so `/ingest/watch` and `/sync/health` no longer drop
  unmapped types — they land under `apple.*` (matching the zip importer).
  Previously such samples were reported as `skipped`.

- **Hardening (Phase 9)**: optional **TOTP MFA** (`/auth/mfa/*`; login
  requires `otp` when enabled), optional **at‑rest media encryption**
  (Fernet, transparent via `app.core.crypto`), and **RGPD erasure**
  (`DELETE /me` cascades all data and purges media/export files). Added a
  `Security` CI workflow (gitleaks, pip‑audit, pnpm audit, Trivy fs, syft
  SBOM) and a gitleaks pre‑commit hook. Migration `0003` adds the MFA
  columns idempotently (ADR‑0004/0005).
- **Automations (Phase 8)**: CRUD for trigger→action rules
  (`/automations`, triggers nfc/shortcut/manual/schedule/api) plus
  `POST /automations/{id}/run` which executes the action — `reminder`
  (returns the message) or `capture` (opens a capture session). Exposed as
  MCP tools `list_automations`/`create_automation`.
- **MCP server (Phase 7)**: a FastMCP server (`mcp/`) exposing hub tools —
  `list_metrics`, `create_metric`, `record_measurement`, `get_measurements`,
  `get_trend`, `get_daily_summary`, `get_photo_analysis`, `compare_photos`,
  `generate_report`, `export_data` — each a thin client of the REST API
  (single source of truth), authenticated with a scoped token. Runnable via
  the `mcp` compose profile; its own lint/type/test CI job.
- **Exports & reports (Phase 6)**: `GET /export?format=csv|json|xlsx|fhir`
  streams a tidy dataset (`date, metric_key, value, unit, source`); the FHIR
  format emits an R4 `Bundle` of `Observation` resources. `POST /reports`
  generates a report (clinical **PDF**, or any export format) as an async
  worker job with an inline fallback when no worker is running;
  `GET /reports/{id}` reports status and `GET /reports/{id}/file` streams the
  result to its owner. Adds `openpyxl` and `fpdf2`.
- **Dashboards (Phase 5)**: `GET /dashboard/{domain}` returns every numeric
  metric of a domain as a rolling series (using each metric's aggregation
  hint). The React app gains a domain tab bar and a dashboard grid that
  renders each series through the single governed chart component.
- **Photo pipeline (Phase 4)**: `POST /ingest/photo` (multipart, scope
  `ingest:photo`) stores the original outside the web root, EXIF‑sanitizes
  and normalizes it (Pillow), then queues an async worker job that runs the
  Ollama vision model for a strict‑JSON silhouette analysis, links the
  previous same‑angle photo for comparison, and injects the AI change as a
  measurement (`source=ai`). Read via `GET /photos`, `/photos/{id}`,
  `/photos/{id}/analysis`, `/photos/compare`, and the authenticated
  `/photos/{id}/file` stream. Ollama URL/models are configurable and mocked
  in tests.
- **Ingestion (Phase 3)**: `POST /ingest/watch` and `POST /ingest/ppc`
  accept generic samples keyed by `metric_key` or by an external
  `healthkit_type`, resolved through a **configurable mapping table**
  (`ingest_mappings`) so new fields are absorbed with no code change;
  unresolved keys are reported, not fatal.
- Mapping management: `GET/POST /ingest/mappings`; seeded global HealthKit
  defaults.
- **Mode B** `POST /capture`: opens a `capture_session` event, records
  weight + photo flags, pre‑fills the latest Watch/CPAP data and returns the
  manual‑only complement form.
- Alembic migration `0002_ingest_mappings` (incremental, per‑table from the
  ORM metadata).

## [0.1.0] — 2026-01

Foundation milestone (specification Phases 1–2).

### Added

- Docker Compose stack: `db` (PostgreSQL 16), `redis`, `api` (FastAPI),
  `worker` (ARQ), `web` (Nginx + React build), optional `mcp`.
- One‑shot `install.sh` bootstrap (build, migrate, seed, admin) and a fully
  commented `.env.example`.
- Authentication: argon2id passwords, JWT access tokens, **rotating and
  revocable** refresh sessions, `/auth/{login,refresh,logout,me}`.
- Scoped, hashed **API tokens** with CRUD and scope enforcement.
- **Dynamic metric registry** (`/metrics`) — add a field at runtime with no
  migration.
- **Measurements**: idempotent batch write, filtered reads, rolling
  aggregation series; **events** with attached measurements.
- Polymorphic typed measurement storage; partial unique indexes for zero
  redundancy; derived metrics marked read‑only.
- Seeded metric **catalogue** (Annexe A, 76 metrics) + initial admin.
- Append‑only **audit log** of every write.
- Alembic initial migration driven by the ORM metadata.
- React (Vite + TS) front: login, token/auth flow (TanStack Query), metric
  catalogue, a governed chart component with a semantic palette, quick weight
  entry.
- Quality tooling: ruff, mypy (strict), ESLint + Prettier, a custom
  structural‑limits checker, pre‑commit config, and GitHub Actions CI with a
  ≥ 80 % coverage gate.
- Documentation: README, architecture and data‑model docs (Mermaid), how‑to
  guides, and ADRs.

### Security

- Security headers + strict CSP (web tier), restricted CORS, non‑root
  hardened container images.

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/v0.1.0
