# Guide — ingestion (Apple Watch, CPAP, capture)

The `/ingest/*` and `/capture` endpoints are implemented (Phase 3). Samples
are mapped to metrics through a **configurable table** (`ingest_mappings`),
so new HealthKit/CPAP fields are absorbed with no code change.

## Apple Watch → `/ingest/watch`

A sample is keyed either by `metric_key` (direct) or by `healthkit_type`
(resolved through the mapping table):

```bash
curl -s $BASE/ingest/watch -H "Authorization: Bearer $WATCH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"date_key":"2026-01-15","samples":[
        {"healthkit_type":"HKQuantityTypeIdentifierOxygenSaturation",
         "value":91,"ts":"2026-01-15T04:12:00Z"},
        {"metric_key":"sleep.total","value":437}
      ]}'
# → {"recorded": 2, "skipped": []}   (unresolved keys are reported, not fatal)
```

CPAP data uses the same shape at `/ingest/ppc` (scope `ingest:ppc`).

A `healthkit_type` that has **no mapping** is no longer skipped: it is
imported under a synthesised `apple.*` metric, created on the fly (same
full-fidelity behaviour as the zip importer). Only samples with neither a
`metric_key` nor a `healthkit_type` are reported in `skipped`.

## iPhone Shortcut sync — `/sync/*`

For a **one-tap, zero-config** sync, the web UI (Import → « Synchro
iPhone ») offers a pre-filled Shortcut:

```bash
# Interactive user session (JWT). Mints an ingest:watch token and returns
# a .shortcut file with the token + endpoint already embedded.
curl -s "$BASE/sync/shortcut?base=https://health.example.com" \
  -H "Authorization: Bearer $ACCESS" -o "Phoenix Sante.shortcut"
```

The Shortcut posts a **flat map** (easy to build on-device) that the
server adapts to the ingest pipeline. Values may be plain text with units
or French separators — they are parsed leniently; unparsable keys are
reported, never fatal:

```bash
curl -s $BASE/sync/health -H "Authorization: Bearer $WATCH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"date_key":"2026-01-15","metrics":{
        "HKQuantityTypeIdentifierBodyMass":"86,2 kg",
        "HKQuantityTypeIdentifierStepCount":"8 542 pas"}}'
# → {"recorded": 2, "skipped": []}
```

`date_key` is optional (defaults to the server's today).

## iPhone → CSV zip (SimpleHealthExportCSV)

Because iOS refuses to import unsigned shortcut files (Apple signing needs
an Apple device), the reliable device path reuses an already-signed
community shortcut, **SimpleHealthExportCSV**, which exports Health data as
one CSV per HealthKit type, zipped, and can upload the zip. Point its
upload at the existing import endpoint:

```
POST /api/v1/imports/apple-health?token=<token>   (scope write:measurements)
Body: multipart/form-data, file field "file" = the .zip
→ 202 { id, status: "queued", ... }   # then poll GET /imports/{id}
```

The token may be given as `?token=` (handy for a Shortcut — no header to
hand-enter) **or** the usual `Authorization: Bearer <token>` header.

The importer **auto-detects** the archive: `export.xml` → Apple's native
format; otherwise it reads every `type,sourceName,…,unit,value` CSV member
into the same full-fidelity storage (`health_samples`) and daily roll-ups,
creating `apple.*` metrics on the fly for unknown types.

## Managing mappings

```bash
# List your mappings + the global defaults
curl -s $BASE/ingest/mappings -H "Authorization: Bearer $ACCESS"

# Add/override a mapping at runtime (no code change)
curl -s $BASE/ingest/mappings -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"source":"watch","external_key":"HKMyCustomType",
       "metric_key":"sleep.hrv"}'
```

## Mode B — `/capture`

Triggered by an NFC tag / Shortcut / button. Opens a `capture_session`
event, records the weight and photo flags, and returns the night's
pre‑filled Watch/CPAP data plus the manual‑only complement form:

```bash
curl -s $BASE/capture -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"weight":86.4,"photo_face":true,"photo_profil":true}'
# → { "event_id": "...", "prefilled": [ ...watch/cpap... ],
#     "complement": [ ...active manual metrics to fill... ] }
```

The actual photo upload + AI analysis attach to this event in Phase 4.

## Also works: scoped tokens + batch measurements

The generic batch endpoint remains available for any script — it is the same
idempotent path the ingestion endpoints build on.

1. Create a token (scopes `ingest:watch`, `write:measurements`):

   ```bash
   curl -s $BASE/tokens -H "Authorization: Bearer $ACCESS" \
     -H 'Content-Type: application/json' \
     -d '{"name":"apple-watch","scopes":["ingest:watch","write:measurements"]}'
   ```

2. From an iOS Shortcut, POST the night's samples:

   ```bash
   curl -s $BASE/measurements -H "Authorization: Bearer $WATCH_TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"items":[
           {"metric_key":"sleep.spo2_min","date_key":"2026-01-15","value":89},
           {"metric_key":"sleep.total","date_key":"2026-01-15","value":437}
         ]}'
   ```

Idempotency means re‑sending the same day is safe (values update in place).

## Phase 3 contract (planned)

- `POST /ingest/watch` — `{ date_key, samples: [{ metric_key | healthkit_type,
  value, unit, ts }] }`, mapped to metrics via a configurable HealthKit table.
- `POST /ingest/ppc` — CPAP machine data (hours, AHI, leaks, pressure).
- `POST /capture` — mode B: opens a `capture_session` event, attaches the
  day's photo, reads the weight, pre‑fills Watch data, and returns the
  manual‑only complement form.
