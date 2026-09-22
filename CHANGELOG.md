# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Photo AI failure no longer marks the photo broken**: the pipeline now
  stores/normalises the image and analyses it in two isolated steps. If
  Ollama is unreachable the photo stays viewable with status `ai_failed`
  ("IA indisponible") instead of the whole photo showing `error`; `error`
  is reserved for an image that genuinely can't be decoded.
- **Home tiles show the current reading**: an instant metric's tile (heart
  rate, SpO2, HRV, respiratory rate, weight…) now shows the **latest raw
  sample's value and its real time**, instead of the day's average stamped
  with the last sample time — which made a live reading look like "2 hours
  ago". Cumulative metrics (steps, energy, water) keep showing the daily
  total. The sparkline still reflects the daily history.
- **Clinical PDF for a doctor**: the report was a bare list of raw metric
  keys with a single average. It now has a **Faits marquants** recap, an
  **Évolution des indicateurs clés** section with per-metric **trend
  line-charts** (drawn as vectors — no chart dependency: weight, HR,
  resting HR, HRV, SpO2, respiratory rate, sleep, steps), and per-domain
  tables (Corps, Coeur, Sommeil, Activite…) showing the human label + unit
  and latest / average / min / max / count. Generation date in the header;
  all text latin-1-sanitised so an unusual label never crashes the render.
- **Faster imports**: the shared importer now commits once per ~50k rows
  (bulk-inserting every 5k) instead of committing every batch, so a
  full native export writes far fewer fsync-bound transactions; timestamp
  parsing is hand-rolled for the canonical Apple format (~3.4× faster than
  `strptime`, and it's called twice per sample); and each HealthKit type's
  metric spec is resolved once and cached. Applies to both the XML and CSV
  paths.

### Added

- **HEIC/HEIF photo support**: Apple devices (and mirror cameras) capture
  HEIC, which PIL and web browsers cannot read — so an uploaded HEIC showed
  as a black "IMAGE ILLISIBLE" tile even though the file was fine. The
  normalizer now registers `pillow-heif`, decodes HEIC/HEIF and re-encodes a
  browser-safe JPEG, and intake accepts `image/heic` / `image/heif`.
  Verified end to end (HEIC upload → normalized → served as an image).
- **Photos tab**: a new "Photos" page shows the progress photos uploaded via
  `POST /ingest/photo` (mirror/device) as a grid — angle (Face/Profil/Dos)
  filter, date, linked weight, processing status, and the **AI (Ollama
  vision) analysis** per photo. Images are fetched with the auth token
  (blob) since the file endpoint is owner-only. Previously the photo
  pipeline had no viewer at all — photos could be uploaded but not seen.
- **Token manager in the web UI**: the Import tab gets a *Jetons d'accès*
  card to create an API token and **tick its scopes** (Photos
  `ingest:photo`, Montre/Santé `ingest:watch`, Mesures `write:measurements`,
  PPC, métriques, lecture seule), see each token's scopes and revoke — so a
  non-technical user can mint the right token (e.g. the `ingest:photo` token
  a photo mirror needs) without curl. The one-off secret is shown once with
  a copy button; the CLI path stays available. Previously the UI could only
  mint a fixed `write:measurements` token, which is why photo uploads 403'd
  with "Missing scope: ingest:photo".
- **Health Auto Export (JSON)**: `POST /sync/auto-export` ingests the JSON
  body posted by the *Health Auto Export* iOS app
  (`{"data":{"metrics":[{"name,units,data:[{date,qty}]}]}}`) — no multipart
  file, unlike the CSV upload. Metric names map to the matching HealthKit
  identifier so they land on the same canonical keys a native export uses
  (and are auto-created when missing); each point is recorded on its own
  date, `qty` or `Avg` taken as the value. Same `write:measurements` token
  (`?token=` in the URL), so the app needs no header. A full history export
  is tens of MB and tens of thousands of points, so the payload is chunked
  (the ingest schema caps a batch at 500) and timestamps are parsed
  timezone-aware (PostgreSQL rejects naive ones); nginx lifts its 25 MB
  body cap on this route. Like the native Apple import, every point is now
  stored as a raw `health_samples` row (so it appears in the **Données**
  browser, not only as a daily tile) **and** folded into a daily
  `measurements` roll-up via the shared `DailyAggregator` — summed for
  steps / distance / energy / exercise minutes, averaged for heart rate /
  SpO2 — so a daily tile is a real total, not the last minute's reading.
  Units are normalised (e.g. SpO2 0.96 → 96 %). Re-pushing a day replaces
  that day's Health-Auto-Export samples, so the every-5-minutes automation
  stays idempotent instead of piling up duplicates.
- **One-tap counters (café, cigarette, eau)**: `POST /sync/tally` adds to a
  metric's *daily total* (read-modify-write) instead of overwriting it, so
  an iPhone Shortcut can tap `{"metric":"habit.cigarettes"}` repeatedly and
  the day's count climbs. Body is `{metric, amount?=1, date_key?}`; the
  token rides in the URL (`?token=`) so no header is needed. Fractional
  amounts work (a half mug of coffee = `amount: 0.5`), and the seeded
  `water.bottles_1_5` feeds the derived `hydration.liters` (× 1.5). Reuses
  the same `write:measurements` token as the CSV upload URL.
- **Biologie → valeurs suivies**: `POST /biology/import` parses a
  **text-based French lab PDF** (pypdf) and records each analyte's current
  value **and its antériorités** (previous value + its own date) as
  measurements under `bio.<key>` metrics — so a blood test becomes real
  tracked curves. Parsing is **catalog-driven** (`biology_catalog`): only
  recognized analytes are recorded, with canonical labels/units, so notes,
  method lines, thresholds and continuation lines (e.g. `soit (IFCC)`)
  never become fake metrics. It handles the real report layouts — name on
  its own line, `percentage then absolute` counts (records the absolute),
  the same analyte in two units, French thousands separators — and matched
  a full BIOGROUP hémogramme + biochimie + bilan on the real PDF: **45
  analyses, 85 values across 4 dates** with zero junk. `DELETE
  /biology/values` (and a "Réinitialiser la biologie" button) purges all
  `bio.*` values and their now-empty metrics to recover from a bad import.
  The source PDF is kept as a `biologie` document. Dossier tab gets an
  "Analyser une prise de sang (PDF)" upload.
- **OCR for scanned PDFs**: a scanned (image-only) lab PDF has no text
  layer, so biology import now falls back to **OCR** (`ocr` service:
  PyMuPDF rasterises each page, Tesseract reads it in French) and feeds the
  result through the same strict catalog — a scanned blood test still
  yields tracked values, and OCR noise cannot create junk metrics because
  unrecognised lines are simply skipped (verified: a fully rasterised
  BIOGROUP report still yields 27 analyses / 50 values, zero junk).
  Tesseract (`tesseract-ocr` + `tesseract-ocr-fra`) is added to the backend
  image; when it is absent the import degrades gracefully (the document is
  still kept). Note: OCR can drop decimal points on dense EFR / blood-gas
  tables, so structured EFR / gaz-du-sang value tracking is intentionally
  not auto-recorded yet — those reports are kept as documents.
- **Visionneuse DICOM**: the Dossier tab gets a built-in DICOM viewer
  (`components/dicom`, using `dicom-parser`) to open the `.dcm` files from
  an imaging CD (scanner, IRM, radio) — entirely in the browser, nothing is
  uploaded. It renders uncompressed monochrome studies (8/16-bit, signed or
  not, little- or big-endian, MONOCHROME1 inverted, rescale slope/intercept
  applied) with window-centre/width controls (auto-fit from the pixel
  range) and a slice slider for a multi-file series, plus a metadata panel
  (patient, modality, study/series, dimensions). Compressed transfer
  syntaxes (JPEG/JPEG2000) are detected and reported with their metadata
  rather than rendered — a full codec stack can come later.
- **Dossier CDA du médecin**: `POST /clinical/import` imports a
  doctor-delivered **French CI-SIS / HL7 CDA** file (namespace-agnostic
  parser reused from the native-export clinical path). Each `<observation>`
  becomes a searchable clinical observation (label / value / unit / date)
  browsable in Santé → Observations cliniques, and the raw CDA is stored
  encrypted as a `cda` document. The Dossier tab gets an "Importer un
  dossier CDA (médecin)" upload.
- **Caregiver report (tout donner au médecin)**: the clinical PDF now also
  prints the care record — Maladies, Traitements, Rendez-vous and a
  Documents médicaux index — right after the recap, so the single exported
  report hands a doctor the metrics *and* the medical history in one file.
- **Suivi médical (conditions, treatments, appointments)**: a new "Suivi"
  tab and APIs to declare maladies (`/conditions`), traitements
  (`/treatments`, with an active toggle) and rendez-vous (`/appointments`),
  including **Apple Calendar (.ics) import** (`POST /appointments/import`,
  deduped by UID) parsed with a dependency-free VEVENT reader. Tables added
  via migration `0007`.
- **Dossier médical (medical documents)**: a new "Dossier" tab and API
  (`/medical/documents`) to upload, list, view and delete medical files —
  ordonnances, imageries + comptes-rendus, biologie (prises de sang), EFR,
  tests de marche, dossier CDA, vaccinations, autre. Files are stored
  encrypted at rest (same crypto layer as photos), typed and dated, and
  purged by RGPD account erasure. Table added via migration `0006`.
- **Home = a health hub**: each `/summary` tile now carries `at` (the
  newest raw sample time), `delta` (day-over-day change), `avg7` (7-day
  average) and `spark` (last 14 daily values). The Accueil tiles show the
  reading time, an evolution arrow, a sparkline and the 7-day average, and
  sleep renders as hours (`6 h 28`). Added HRV and respiratory rate to the
  headline set.
- **Santé tab no longer blank**: it now leads with a **Signes vitaux —
  tendances** section (heart rate, resting HR, HRV, SpO2, respiratory rate,
  sleep charts) so a CSV-only import (no workouts/ECG/routes) still shows
  content, plus a hint explaining those records come from the native Health
  export.
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
