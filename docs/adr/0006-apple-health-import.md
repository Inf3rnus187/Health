# ADR 0006 — Apple Health export import

- Status: accepted
- Date: 2026-09

## Context

Apple Health exports a single archive whose `export.xml` is frequently
hundreds of megabytes and holds millions of `<Record>` samples (heart
rate every few minutes, steps in tiny increments, …) plus `<Workout>`
entries. Users want their history in Phoenix Health Hub. Three tensions
shape the design:

1. The fact table keeps **one value per metric per day** with no
   redundancy (§5.3, ADR on the data model); raw per-sample rows do not
   belong there.
2. The file is far too large to upload through the browser (Nginx caps
   the body at 25 MB) or to hold in memory as a DOM.
3. XML from an untrusted archive can carry entity-expansion attacks.

## Decision

A dedicated importer under `app/services/apple_health/`, driven by a
small CLI (`python -m app.cli.import_apple_health`) run inside the API
container against a mounted file.

- **Streaming parse.** `defusedxml.ElementTree.iterparse` reads the file
  incrementally; the tree is cleared after every top-level element, so
  memory stays flat regardless of file size. `defusedxml` blocks entity
  and external-reference attacks while still accepting the internal DTD
  subset Apple emits.
- **Daily aggregation.** Samples are folded into one value per
  `(metric key, day)` using each metric's declared aggregation
  (`sum` for steps/energy/minutes/distance, `avg`/`min`/`max` for heart
  rate and SpO2, `last` for weight/BMI). One HealthKit type may fan out
  to several metrics (heart rate → avg/min/max). Sleep stages are summed
  in minutes and bucketed to the **wake-up** day; workouts contribute a
  daily count, duration, energy and distance.
- **Unit conversion.** Each record's own unit (`mi`, `lb`, `mL`, `degF`,
  fractional `%`, …) is converted to the metric's canonical unit; unknown
  pairs pass through unchanged so an unexpected unit never aborts a run.
- **Dynamic registry, no migration.** Target metrics that do not yet
  exist are created as ordinary `metric_definitions` rows at import time
  (ADR 0002). New domains (`activity`, `heart`, `vitals`, `nutrition`,
  `fitness`) therefore appear automatically; the dashboard tabs are
  derived from the live catalogue rather than hard-coded.
- **Idempotent.** Values are upserted through the normal measurement
  path, so re-running overwrites each day's row with the same aggregate —
  safe to repeat after a newer export.

## Consequences

- A multi-hundred-MB export imports in bounded memory; only compact daily
  rows land in the database (tens of thousands, not millions).
- Sub-daily granularity is intentionally lost — consistent with the
  zero-redundancy model. ECG waveforms (`electrocardiograms/*.csv`) and
  GPS routes (`workout-routes/*.gpx`) are **not** health metrics and are
  skipped; they can be added later as attachments if needed.
- `defusedxml` is now a direct dependency.
