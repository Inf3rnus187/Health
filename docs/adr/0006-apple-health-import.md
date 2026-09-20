# ADR 0006 — Apple Health import (full fidelity)

- Status: accepted
- Date: 2026-09 (supersedes the daily-only first draft)

## Context

Apple Health exports a `.zip` whose `export.xml` is frequently hundreds of
megabytes and holds **millions** of `<Record>` samples, plus `<Workout>`
entries, ECG voltage CSVs and GPS routes. Users want *all* of it, and they
want to import it from the web UI — not a CLI. A first attempt stored only
one aggregated value per day and shipped a CLI; that was rejected: it threw
away the raw data and was unusable for a non-technical user.

## Decision

Keep every record, at full resolution, imported from the browser or the
API through a background job.

- **Raw storage.** New tables hold the data verbatim: `health_samples`
  (every quantity/category sample with its exact timestamp, value, unit and
  device), `workouts`, `ecg_records` and `route_files`. ECG voltages and
  GPX bytes are large, so they live on disk (encrypted, under the media
  volume) with only metadata in the database.
- **Streaming + bulk insert.** `defusedxml.iterparse` reads `export.xml`
  incrementally (straight out of the zip) and the tree is cleared after
  every top-level element, so memory stays flat. Samples are bulk-inserted
  with SQLAlchemy Core in batches, so millions of rows load in bounded
  memory.
- **Background job.** The upload streams to the exports volume; an
  `import_jobs` row tracks status/phase/counts; an ARQ worker
  (`import_apple_health_job`, long `job_timeout`) runs the import while the
  page polls for progress. Nginx allows an unbounded body and disables
  request buffering on the upload route only.
- **Daily roll-up cache.** Charts cannot plot millions of points, so the
  same pass also caches one value per metric per day in `measurements`
  (sum/avg/last per the metric's aggregation). This is an explicit derived
  cache over the raw data, not the source of truth.
- **Dynamic registry.** Unmapped HealthKit types are still imported under a
  synthesised `apple.<type>` metric created on the fly (ADR 0002) — nothing
  is dropped. Dashboard tabs are derived from the live catalogue.
- **Idempotent.** A re-import first deletes the user's prior Apple-sourced
  rows (and their on-disk blobs), then re-inserts — no duplicates.
- **Scalable browsing.** `GET /samples` is filtered (metric, date range)
  and paginated with a total count; the UI shows one page at a time and can
  never load the whole history into the browser.
- **ECG quality filter.** Traces whose classification reads *Poor
  Recording* / *mauvais enregistrement* are dropped at import (no row, no
  file).
- **Viewing signals.** `GET /ecg/{id}/series` returns a downsampled voltage
  trace and `GET /routes/{id}/track` the route coordinates. The ECG
  waveform is drawn as inline SVG (self-only). The GPS route is shown on a
  real Leaflet + OpenStreetMap map; this is the single CSP exception
  (`img-src https://*.tile.openstreetmap.org`) and needs Internet for the
  tiles. Raw CSV/GPX stay downloadable.
- **CDA.** `export_cda.xml` is streamed too: each value-bearing
  `<observation>` (label, value, unit, date) is stored in
  `clinical_observations` and browsed via `GET /clinical/observations`
  (searchable, paginated); the raw XML is kept for download.

## Live sync (iPhone Shortcut)

The `.zip` is the exhaustive path but is a manual, occasional action. For a
daily top-up we add a **one-tap** path that needs no app and no
configuration:

- `GET /sync/shortcut` (interactive user) mints a scoped `ingest:watch`
  token and returns a **pre-filled, unsigned `.shortcut`** built with
  `plistlib` — the token and the `/sync/health` URL are embedded, so the
  user never picks data types or edits JSON. Only action identifiers and
  the variable-token serialisation that are stable across Shortcuts
  versions are emitted, so the file imports cleanly (it does require the
  one-time iOS *Allow Untrusted Shortcuts* toggle).
- `POST /sync/health` accepts a **flat** `{date_key?, metrics:{type:
  value}}` map — trivial to assemble in Shortcuts — and adapts it to the
  ingest pipeline. Values are parsed leniently (`"86,2 kg"`, `"8 542
  pas"`); unparsable keys are reported, never fatal.
- Ingestion was hardened so this actually lands: a `healthkit_type` with
  no user mapping now resolves through the Apple spec and **auto-creates**
  its metric (`MetricCache`), exactly like the zip importer. This also
  changes `/ingest/watch`: previously-skipped unmapped types are now
  recorded under `apple.*` (nothing is silently dropped).

Scope note: the shipped Shortcut reliably syncs the day's weight.
Auto-reading dozens of Health metrics through Shortcuts is intentionally
not pre-built — the Health *read* actions vary across iOS versions and
cannot be verified without a device; the `.zip` covers that end to end.

## Consequences

- The database grows to the true size of the export (millions of rows);
  this is accepted as the cost of full fidelity. Postgres indexes on
  `(user_id, metric_id, start_at)` keep browsing fast.
- ECG/GPX bytes stay on disk; the DB holds metadata plus download routes.
- `defusedxml` is a direct dependency; large uploads spool onto the durable
  volume (`TMPDIR`) rather than the container's `/tmp`.
