# Guide — ingestion (Apple Santé, Health Auto Export, montre, PPC, capture)

Every channel writes the **same canonical metric** for the same concept
(e.g. `body.weight`, `activity.steps`, `bio.hba1c`), resolved through the
full HealthKit catalog (iOS 26 SDK: 121 quantity + 72 category types) and a
**configurable mapping table** (`ingest_mappings`). Raw samples are kept;
daily values are rebuilt from them with one rule (one Apple channel per
day — native export and Health Auto Export are never added up — plus the
other sources). Required token scope per route:
[API reference](../api.md).

| Channel | Route | Token scope |
|---------|-------|-------------|
| Full Apple Health export (`export.zip`) | `POST /imports/apple-health` | `write:measurements` (+ `?token=`) |
| Health Auto Export (daily JSON) | `POST /sync/auto-export` | `write:measurements` (+ `?token=`) |
| SimpleHealthExportCSV (zip of CSV) | `POST /imports/apple-health` | `write:measurements` (+ `?token=`) |
| iPhone Shortcut (flat map) | `POST /sync/health` | `ingest:watch` |
| One-tap counts: `{"metric": key, "amount"?}` — water bottle, coffee, cigarette, pee (`elimination.urination`, timed), clock in / out (`work.start` / `work.end`) | `POST /sync/tally` | `write:measurements` (+ `?token=`) |
| Past clock-in / clock-out logs (txt, csv, json; `?dry_run=true` reads only) | `POST /work/import` | `write:measurements` (+ `?token=`) |
| App exports and receipts as traces — Uber, Uber Eats, Navigo, parking, hotels, expense reports, bank statements (CSV / XLSX / JSON) and receipts (PDF, photo); `files` + `kinds` (`auto` guesses), a receipt and its expense line are merged, `meals=true` logs deliveries as priced meals | `POST /traces/import` | session or `hub:full` |
| iPhone Shortcut histories — one time stamp per line, one kind per file (`files` + optional `keys`; clock-ins and clock-outs paired, counters fill empty days, pee de-duplicated) | `POST /logs/import` | `write:measurements` (+ `?token=`) |
| Watch / HealthKit samples | `POST /ingest/watch` | `ingest:watch` |
| CPAP | `POST /ingest/ppc` | `ingest:ppc` |
| Progress photos | `POST /ingest/photo` | `ingest:photo` |
| Pee at a given time (web Journal, `{"at": …}`) | `POST /journal/urination` | `write:measurements` (+ `?token=`) |
| Meal: form `description`, `file` (photo), `meal_type`?, `eaten_at`? | `POST /meals` (multipart) | `write:measurements` (+ `?token=`) |
| Any script (sets — **replaces** — a day's value) | `POST /measurements` | `write:measurements` |

iPhone Shortcuts step by step (one token, one rule for every count, one
for meals): [usage guide](utilisation.md#raccourcis-iphone--une-seule-règle).

## Health Auto Export (JSON)

The *Health Auto Export* iOS app pushes Health data on a schedule.

1. Web app › **Import › « Health Auto Export (JSON) » › Créer l'URL** — it
   mints a `write:measurements` token and shows
   `https://<hub>/api/v1/sync/auto-export?token=<token>`.
2. In the app: new **Automation** of type **REST API**, paste the URL,
   method **POST**, format **JSON**, data type **Health Metrics**, the
   metrics you want (all is fine), and a sync schedule. A first run with a
   long date range back-fills the history.

What the server does with a payload
(`{"data": {"metrics": [{"name", "units", "data": [{"date", "qty"}]}]}}`):

- every spelling the app has used for a metric maps to its HealthKit type
  (`walking_running_distance`, `weight_body_mass`, `blood_oxygen_saturation`…),
  so it lands on the same metric as the native export;
- `blood_pressure` is split into systolic / diastolic; `sleep_analysis`
  into sleep stages (`sleep.asleep`, `sleep.deep`, `sleep.rem`…, hours →
  minutes); percentages (already 0–100) are never scaled twice;
- each point is stored as a raw sample; re-pushing a day replaces that
  day's Health Auto Export samples (idempotent), and the daily values are
  recomputed from the pushed day onward;
- workouts in the payload are not imported (use the full export for them);
- a name outside the catalog is still stored, under an `apple.<name>`
  metric; points without a date or a number (`qty`, or `Avg` for heart
  rate) are listed in the response's `skipped`.

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

A `healthkit_type` that has **no mapping** is not skipped: it resolves
through the HealthKit catalog (French label, domain, unit, daily rule), or
to a synthesised `apple.*` metric for a type outside the SDK catalog. Only
samples with neither a `metric_key` nor a `healthkit_type` are reported in
`skipped`.

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
resolving each type through the HealthKit catalog.

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

Photos are sent separately to `POST /ingest/photo` (multipart: `file`,
`angle` = `face` / `profil` / `dos`, optional `date_key`, `weight`) with an
`ingest:photo` token; the analysis runs in the worker.

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
