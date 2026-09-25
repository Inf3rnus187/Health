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
| One-tap counts: `{"metric": key, "amount"?, "date_key"?}` — water bottle, coffee, cigarette, urge broken, pee (`elimination.urination`, timed), clock in / out (`work.start`, `work.remote_start`, `work.end`, `work.remote_end`). `amount`: `1` by default, negative takes back, `0` confirms a day at zero (a value 0 is stored, instead of a day without data); `date_key`: today (local) by default — pees and clock taps only accept today, and clock taps only `amount` 1 | `POST /sync/tally` | `write:measurements` (+ `?token=`) |
| Clock in / out: JSON `kind` (`in` / `out`), `at`? (ISO; default now, without offset = local), `place`? (`site` default / `remote`; a clock-out closes the open session wherever it is) | `POST /work/clock` | `write:measurements` (+ `?token=`) |
| Past clock-in / clock-out logs (txt, csv, json; `?dry_run=true` reads only) | `POST /work/import` | `write:measurements` (+ `?token=`) |
| App exports and receipts as traces — Uber, Uber Eats, Navigo, parking, hotels, expense reports, bank statements (CSV / XLSX / JSON), receipts (PDF, photo), Lucca expense-report PDFs (one trace per expense, the PDF kept untouched), ticket exports (NinjaOne… CSV: the `person`'s actions, one `activite` trace a day), WhatsApp chat exports (`.txt`: the `person`'s messages and calls). Multipart `files` + `kinds` (one per file, same order: `transport`, `taxi`, `parking`, `livraison`, `repas`, `hotel`, `frais`, `activite` or `auto` — guessed), form `person`? (whose tickets / messages; default the most active author, or « Moi » in a chat — the preview lists the others); a receipt and its expense line are merged; `?meals=true` logs deliveries and bought meals as priced meals, `?dry_run=true` reads only | `POST /traces/import` | session or `hub:full` |
| One proof or trace by hand: multipart `occurred_at`* (ISO; without offset = local), `kind` (`capture` by default; proofs `appel`, `sms`, `mail`, `capture`, `note`, `document`, `autre`, or a trace kind above), `title`, `description`, `count` (1–10000), `absence_id`, `file` (30 MB in the API, 25 MB through nginx), trace fields `ended_at`, `place`, `amount`, `currency` (`EUR`), `meal=true` (a `livraison` / `repas` trace is also logged as a priced meal and read by the AI) | `POST /evidence` | session or `hub:full` |
| Absences from an HR export (Lucca…: CSV, XLSX, JSON): multipart `files`, form `person`? (a manager's export; default the one with the most rows), `?dry_run=true` reads only; nothing added twice | `POST /absences/import` | session or `hub:full` |
| A night the watch missed: JSON `bedtime`, `wake_time` (ISO; without offset = local; 20 h at most), `awakenings`? (0–100) — a raw `manual` sleep sample plus that day's `sleep.asleep` | `POST /sleep/nights` (`DELETE /sleep/nights/{id}`) | session or `hub:full` |
| iPhone Shortcut histories — one time stamp per line, one kind per file (`files` + optional `keys`; clock-ins and clock-outs paired, counters fill empty days, pee de-duplicated) | `POST /logs/import` | `write:measurements` (+ `?token=`) |
| Watch / HealthKit samples | `POST /ingest/watch` | `ingest:watch` |
| CPAP | `POST /ingest/ppc` | `ingest:ppc` |
| Progress photos | `POST /ingest/photo` | `ingest:photo` |
| Pee at a given time (web Journal, `{"at": …}`) | `POST /journal/urination` | `write:measurements` (+ `?token=`) |
| Meal: form `description`, `file` (plate photo), `photos` (repeated, up to 6: box, sachet, nutrition table), `foods` (JSON `[{"food_id","grams"}]`), `meal_type`?, `eaten_at`? | `POST /meals` (multipart) | `write:measurements` (+ `?token=`) |
| Meal changed afterwards: fields and foods | `PUT /meals/{id}` (JSON) | `write:measurements` |
| Medication dose by name (iPhone Shortcut): JSON `treatment` (accents and case ignored; the start of a word, 3 letters or more, is enough), `taken_at`? (never more than 10 min ahead), `status`? (`taken`/`skipped`), `dose`? (default: the treatment's), `note`? | `POST /medications/take` | `write:measurements` (+ `?token=`) |
| Medication dose of a treatment (web): same JSON without `treatment` | `POST /treatments/{id}/intakes` | `write:measurements` (+ `?token=`) |
| Meal photo added afterwards (the plate's when it has none) / removed | `POST /meals/{id}/photos` (multipart `file`), `DELETE /meals/{id}/photo`, `DELETE /meals/{id}/photos/{photo_id}` — `?read=false` to change several, then read once | `write:measurements` |
| Food sheet (« Mes aliments »): JSON `name`*, `brand`, `aliases` (comma-separated), `package_g`, `unit_name` / `unit_g` (« tomate », 120), `portion_g` (usually eaten, g: counted when a meal gives no quantity), `per_100g` (`energy_kcal`, `protein_g`, `carbs_g`, `sugars_g`, `fat_g`, `sat_fat_g`, `fiber_g`, `sodium_mg`), `note`, `source`, `barcode` (digits) | `POST /foods`, `PUT /foods/{id}`, `DELETE /foods/{id}` (`GET /foods`: `read:all`) | `write:measurements` |
| Food photo: multipart `file`, form `kind` (`pack` default, or `label`) | `POST /foods/{id}/photos`, `DELETE /foods/{id}/photos/{photo_id}` | `write:measurements` |
| Read a pack or its nutrition table with the vision model: multipart `file` → a proposal (`name`, `brand`, `package_g`, `per_100g`), nothing saved; runs inside the API, 100 s at most | `POST /foods/read-label` | `write:measurements` |
| Ciqual 2025 reference values (offline table): `?q=` (2–100 characters, every word must match), `limit` (1–50, default 20); one food by code | `GET /ciqual`, `GET /ciqual/{code}` | `read:all` |
| A pack's barcode read on a photo (camera or gallery), decoded on the hub offline (EAN-13, EAN-8, UPC): multipart `file` → `barcodes`, `food` (my food with that barcode or null), `product` (Open Food Facts proposal only when `FOOD_LOOKUP_ONLINE=true`, else null), `online`, `note`. Nothing saved, the photo is not kept | `POST /foods/scan` | `write:measurements` (+ `?token=`) |
| A packaged food by barcode (8–14 digits) from Open Food Facts → a proposal, nothing saved. Off by default: `422` unless `FOOD_LOOKUP_ONLINE=true`; only the barcode is sent | `GET /openfoodfacts/{barcode}` | `write:measurements` |
| Any script (sets — **replaces** — a day's value) | `POST /measurements` | `write:measurements` |

iPhone Shortcuts step by step (one token, one rule for every count, one
for meals): [usage guide](utilisation.md#raccourcis-iphone--une-seule-règle).

## Upload size limits

- **nginx** (`nginx/default.conf`) caps every request body at **25 MB**
  (`client_max_body_size 25m`: all the files of one request together),
  except `POST /imports/apple-health` (no limit, streamed to disk, 1 h
  timeouts) and `POST /sync/auto-export` (no limit, 10 min).
- **Photos** — progress photos, meal photos (each one), food photos:
  `MAX_UPLOAD_MB` (15 by default) per image, checked by the API.
- **Evidence files** (`POST /evidence`): 30 MB in the API, so 25 MB in
  practice behind nginx; medical documents: 25 MB.
- A body over the nginx cap is refused by nginx (`413`) before it
  reaches the API.

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

A pre-filled Shortcut can be built by the API only — the web UI does
not offer it (iOS refuses unsigned `.shortcut` files, see the CSV zip
path below, which is what the web card « Synchro iPhone (export CSV) »
sets up):

```bash
# Interactive user session (JWT) only, never a token. Mints an
# ingest:watch token and returns a .shortcut file with the token +
# endpoint already embedded.
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
one CSV per HealthKit type, zipped, and can upload the zip. The web card
**Import › « Synchro iPhone (export CSV) » › « Créer l'URL d'upload »**
mints a `write:measurements` token (named « iPhone (CSV) ») and shows,
once, `https://<hub>/api/v1/imports/apple-health?token=<token>` with the
recipe; point the shortcut's upload at it:

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
resolving each type through the HealthKit catalog. When a job ends
`done`, the reconciliation (`reconcile_data`: merge duplicate keys,
rebuild daily values from the raw data) is queued by itself — nothing to
launch by hand.

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
