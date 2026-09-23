# Référence de l'API

Généré depuis le code (`python -m app.cli.api_doc`) — ne pas éditer à la
main. Base : `/api/v1`. Documentation interactive : `/api/v1/docs`
(Swagger) et `/api/v1/redoc`.

**Accès** — *Public* : sans authentification. *Tout jeton* : session ou
n'importe quel jeton. *`scope`* : session, jeton `hub:full`, ou jeton
portant ce scope. *Session / hub:full* : connexion web ou jeton
`hub:full`. *Session uniquement* : connexion web (jamais un jeton).
Un jeton s'envoie en `Authorization: Bearer <jeton>` ; « + ?token= »
signale qu'il est aussi accepté en paramètre d'URL.


## Authentification et 2FA

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/auth/login` | Public | JSON `LoginRequest` (email, password, otp) | Authenticate and return an access+refresh token pair. |
| POST | `/auth/logout` | Public | JSON `RefreshRequest` (refresh_token) | Revoke the session behind the given refresh token. |
| GET | `/auth/me` | Tout jeton | — | Return the currently authenticated user. |
| POST | `/auth/mfa/disable` | Session uniquement | JSON `MfaVerify` (code) | Disable MFA after verifying a code. |
| POST | `/auth/mfa/enable` | Session uniquement | JSON `MfaVerify` (code) | Enable MFA after verifying a code. |
| POST | `/auth/mfa/setup` | Session uniquement | — | Assign a TOTP secret and return its otpauth URI (not yet enabled). |
| POST | `/auth/refresh` | Public | JSON `RefreshRequest` (refresh_token) | Rotate a refresh token and return a new pair. |
| GET | `/auth/scopes` | Tout jeton | — | How the caller is authenticated and what it may do (MCP gate). |

## Compte

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| DELETE | `/me` | Session uniquement | — | Permanently erase the caller's account and all their data. |

## Jetons d'accès (API)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/tokens` | Session uniquement | — | List the caller's API tokens (secrets are never returned). |
| POST | `/tokens` | Session uniquement | JSON `TokenCreate` (name, scopes, expires_at) | Mint a scoped token; the secret is returned only once. |
| DELETE | `/tokens/{token_id}` | Session uniquement | `token_id` | Revoke one of the caller's API tokens. |

## Accueil

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/summary` | `read:all` | — | Return the latest value of each available headline metric. |

## Catalogue des métriques

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/catalog` | Tout jeton | `domain`?, `source`?, `active`? | Alias of ``GET /metrics`` (avoids client-side 'metrics' blockers). |
| GET | `/catalog/domains` | Tout jeton | — | French name of every metric domain (tabs, reports, MCP). |

## Métriques

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/metrics` | Tout jeton | `domain`?, `source`?, `active`? | List metric definitions, filterable by domain/source/active. |
| POST | `/metrics` | `write:metrics` | JSON `MetricCreate` (key, label, domain, data_type, unit, source, enum_options, min_value, max_value, aggregation_hint, formula) | Register a new metric at runtime. |
| GET | `/metrics/{key}` | Tout jeton | `key` | Return one metric definition by key. |
| PATCH | `/metrics/{key}` | `write:metrics` | `key`, JSON `MetricUpdate` (label, unit, enum_options, min_value, max_value, aggregation_hint, formula, is_active) | Update a metric's label, bounds, options or active flag. |
| GET | `/metrics/{key}/overview` | `read:all` | `key`, `days`? | Latest reading, day value, averages, sources and daily series. |

## Valeurs journalières

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/measurements` | `read:all` | `metric_key`?, `start`?, `end`?, `event_id`? | Return raw measurements matching the given filters. |
| POST | `/measurements` | `write:measurements` | JSON `MeasurementBatch` (items) | Record one or more measurements (idempotent, batch). |
| POST | `/measurements/delete` | `write:measurements` | JSON `IdList` (ids) | Delete several measurements at once (owner-scoped). |
| GET | `/measurements/series` | `read:all` | `metric_key`, `agg`?, `window`? | Return a rolling-aggregated series for a numeric metric. |
| DELETE | `/measurements/{measurement_id}` | `write:measurements` | `measurement_id` | Delete one measurement (owner-scoped). |

## Relevés bruts

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/samples` | `read:all` | `metric_key`?, `start`?, `end`?, `limit`?, `offset`? | Return one filtered page of raw samples plus the total count. |

## Tendances

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/trends` | `read:all` | `metric_key`, `bucket`? | Return a metric's values bucketed by the given period. |

## Tableaux de bord

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/dashboard/{domain}` | `read:all` | `domain`, `window`? | Return rolling series for every numeric metric of a domain. |

## Données (inventaire, réconciliation)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/data/inventory` | Session / hub:full | — | Every metric with data: raw samples and daily values per source. |
| POST | `/data/reconcile` | Session / hub:full | — | Queue: merge duplicate keys, rebuild daily values from raw data. |

## Événements

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/events` | `read:all` | `event_type`?, `start`?, `end`? | Return the user's events, newest first. |
| POST | `/events` | `write:measurements` | JSON `EventCreate` (type, occurred_at, date_key, meta, source) | Open a new event (day, night, workout block, capture...). |
| POST | `/events/{event_id}/measurements` | `write:measurements` | `event_id`, JSON `MeasurementBatch` (items) | Attach measurements to an existing event. |

## Ingestion (montre, PPC, photo)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/ingest/mappings` | Tout jeton | — | List the caller's mappings plus the global defaults. |
| POST | `/ingest/mappings` | Session / hub:full | JSON `MappingCreate` (source, external_key, metric_key) | Add or override an external-key → metric-key mapping. |
| POST | `/ingest/photo` | `ingest:photo` | form `file`, form `angle`, form `date_key`, form `weight` | Receive a photo, store it, and queue the analysis pipeline. |
| POST | `/ingest/ppc` | `ingest:ppc` | JSON `IngestPayload` (date_key, samples) | Ingest CPAP machine data (hours, AHI, leaks, pressure). |
| POST | `/ingest/watch` | `ingest:watch` | JSON `IngestPayload` (date_key, samples) | Ingest Apple Watch / HealthKit samples (night + previous day). |

## Synchro iPhone et Health Auto Export

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/sync/auto-export` | `write:measurements` + ?token= | JSON libre | Ingest a Health Auto Export JSON payload (JSON body, no file). |
| POST | `/sync/health` | `ingest:watch` | JSON `HealthSyncPayload` (date_key, metrics) | Ingest a flat ``{healthkit_type: value}`` map (Shortcut-friendly). |
| GET | `/sync/shortcut` | Session uniquement | `base`? | Mint an ingest token and return a pre-filled ``.shortcut``. |
| POST | `/sync/tally` | `write:measurements` + ?token= | JSON `TallyPayload` (metric, amount, date_key) | Add to a daily counter (café, cigarette, bouteille d'eau). |

## Import Apple Santé

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/imports` | `write:measurements` | — | List the caller's recent import jobs. |
| POST | `/imports/apple-health` | `write:measurements` + ?token= | form `file` | Store the uploaded export and queue a background import. |
| POST | `/imports/reset` | Session / hub:full | — | Delete every Apple-imported sample, workout, ECG and route. |
| GET | `/imports/{job_id}` | `write:measurements` | `job_id` | Return the status of one import job. |

## Capture

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/capture` | `write:measurements` | JSON `CaptureRequest` (date_key, weight, photo_face, photo_profil) | Start a capture session and return the day's complement form. |

## Séances, ECG, parcours

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/ecg` | `read:all` | — | List the caller's ECG records. |
| GET | `/ecg/{record_id}/file` | `read:all` | `record_id` | Download one ECG trace as CSV. |
| GET | `/ecg/{record_id}/series` | `read:all` | `record_id` | Return one ECG's downsampled voltage trace. |
| GET | `/routes` | `read:all` | — | List the caller's GPS routes. |
| GET | `/routes/{record_id}/file` | `read:all` | `record_id` | Download one route as GPX. |
| GET | `/routes/{record_id}/track` | `read:all` | `record_id` | Return one route's coordinates for drawing. |
| GET | `/workouts` | `read:all` | `limit`?, `offset`? | List the caller's workouts, newest first. |

## Dossier médical et documents

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/medical/documents` | Session / hub:full | — | List the caller's medical documents, newest first. |
| POST | `/medical/documents` | Session / hub:full | form `file`, form `kind`, form `title`, form `doc_date`, form `notes` | Store an uploaded medical document with its type and date. |
| POST | `/medical/documents/analyze-all` | Session / hub:full | — | Queue every document of the caller for AI reading. |
| DELETE | `/medical/documents/{doc_id}` | Session / hub:full | `doc_id` | Delete one of the caller's medical documents. |
| POST | `/medical/documents/{doc_id}/analyze` | Session / hub:full | `doc_id` | Queue one document for (re-)analysis by the document model. |
| GET | `/medical/documents/{doc_id}/file` | Session / hub:full | `doc_id` | Return one document's decrypted bytes for viewing/download. |
| GET | `/medical/documents/{doc_id}/text` | Session / hub:full | `doc_id` | The text the AI reads from a document (OCR for a scan). |
| GET | `/medical/record` | Session / hub:full | — | Documents, suggestions, results and chronology of the caller. |

## Prises de sang (PDF)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/biology/import` | Session / hub:full | form `file` | Parse a lab PDF into measurements and keep the source document. |
| DELETE | `/biology/values` | Session / hub:full | — | Delete all imported biology values and their bio.* metrics. |

## Dossier CDA

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/clinical/document` | `read:all` | — | Return the stored CDA document summary, or null. |
| GET | `/clinical/document/file` | `read:all` | — | Download the raw CDA XML document. |
| POST | `/clinical/import` | Session / hub:full | form `file` | Import a doctor-delivered CDA (French CI-SIS / HL7 CDA) file. |
| GET | `/clinical/observations` | `read:all` | `search`?, `limit`?, `offset`? | Return one page of clinical observations (searchable by label). |

## Maladies

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/conditions` | Session / hub:full | — | List the caller's conditions. |
| POST | `/conditions` | Session / hub:full | JSON `ConditionIn` (name, code, status, onset_date, notes) | Declare a condition. |
| DELETE | `/conditions/{cid}` | Session / hub:full | `cid` | Delete a condition. |
| PUT | `/conditions/{cid}` | Session / hub:full | `cid`, JSON `ConditionIn` (name, code, status, onset_date, notes) | Replace a condition. |

## Traitements

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/treatments` | Session / hub:full | — | List the caller's treatments. |
| POST | `/treatments` | Session / hub:full | JSON `TreatmentIn` (name, dose, frequency, start_date, end_date, active, notes) | Add a treatment. |
| DELETE | `/treatments/{tid}` | Session / hub:full | `tid` | Delete a treatment. |
| PUT | `/treatments/{tid}` | Session / hub:full | `tid`, JSON `TreatmentIn` (name, dose, frequency, start_date, end_date, active, notes) | Replace a treatment (e.g. toggle active, change dose). |

## Rendez-vous

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/appointments` | Session / hub:full | — | List the caller's appointments. |
| POST | `/appointments` | Session / hub:full | JSON `AppointmentIn` (title, starts_at, ends_at, practitioner, location, notes) | Add a manual appointment. |
| POST | `/appointments/import` | Session / hub:full | form `file` | Import appointments from an Apple Calendar (.ics) export. |
| DELETE | `/appointments/{aid}` | Session / hub:full | `aid` | Delete an appointment. |

## Suivi

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/care/overview` | Session / hub:full | — | Each declared condition with its indicators and documents. |

## Évolution (marqueurs, poids, photos)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/evolution/markers` | `read:all` | — | Validated metabolic / liver markers from the latest data. |
| POST | `/evolution/profile` | `write:measurements` | JSON `ProfileIn` (waist_cm, height_cm, birth_year, cap_db_m, lsm_kpa, date_key) | Record waist / height / birth year, then return the markers. |
| POST | `/evolution/reanalyze-all` | Session / hub:full | — | Re-run the current method over every photo, oldest first. |
| GET | `/evolution/trend` | `read:all` | — | Per-angle, per-criterion long-term photo score evolution. |

## Photos

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| DELETE | `/photos` | Session / hub:full | — | Delete every photo of the caller (files + analyses + rows). |
| GET | `/photos` | `read:all` | `angle`? | List the caller's photos (optionally filtered by angle). |
| GET | `/photos/compare` | `read:all` | `from`, `to` | Return two photos with their analyses for a before/after view. |
| DELETE | `/photos/{photo_id}` | Session / hub:full | `photo_id` | Delete one of the caller's photos. |
| GET | `/photos/{photo_id}` | `read:all` | `photo_id` | Return one photo's metadata. |
| GET | `/photos/{photo_id}/analysis` | `read:all` | `photo_id` | Return the latest AI analysis for one photo. |
| POST | `/photos/{photo_id}/analyze` | Session / hub:full | `photo_id` | Re-queue the normalize + AI analysis for an existing photo. |
| GET | `/photos/{photo_id}/file` | `read:all` | `photo_id` | Return a photo's file (decrypted, normalized if ready) to its owner. |

## Rapports

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/reports` | `read:all` | — | List the caller's recent reports. |
| POST | `/reports` | `read:all` | JSON `ReportCreate` (type, period_start, period_end, params) | Queue a report; build it inline if no worker is available. |
| GET | `/reports/{report_id}` | `read:all` | `report_id` | Return a report's status and metadata. |
| GET | `/reports/{report_id}/file` | `read:all` | `report_id` | Stream a finished report file to its owner. |

## Export

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/export` | `read:all` | `format`?, `domain`?, `from`?, `to`? | Stream a tidy export in the requested format. |

## Automatisations

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/automations` | Session / hub:full | — | List the caller's automations. |
| POST | `/automations` | Session / hub:full | JSON `AutomationCreate` (name, trigger, action, is_active) | Create a new automation. |
| DELETE | `/automations/{automation_id}` | Session / hub:full | `automation_id` | Delete an automation. |
| GET | `/automations/{automation_id}` | Session / hub:full | `automation_id` | Return one automation. |
| PATCH | `/automations/{automation_id}` | Session / hub:full | `automation_id`, JSON `AutomationUpdate` (name, action, is_active) | Update an automation's name, action or active flag. |
| POST | `/automations/{automation_id}/run` | `write:measurements` | `automation_id` | Execute an automation's action and return a result summary. |

## Journal (pipi, repas)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/journal/urination` | `read:all` | `day`? | A day's urinations (default today) with their times. |
| POST | `/journal/urination` | `write:measurements` + ?token= | JSON `UrinationIn`? (at) | Record one urination (now unless ``at`` is given). |
| DELETE | `/journal/urination/{sample_id}` | `write:measurements` | `sample_id` | Delete one urination entry. |
| GET | `/meals` | `read:all` | `start`?, `end`? | Meals between two days (default: the last 7 days), newest first. |
| POST | `/meals` | `write:measurements` + ?token= | form `meal_type`, form `eaten_at`, form `description`, form `price`, form `file` | Log a meal (photo and/or description), then read it with the AI. |
| DELETE | `/meals/{meal_id}` | `write:measurements` | `meal_id` | Delete a meal, its photo and its nutrients. |
| GET | `/meals/{meal_id}` | `read:all` | `meal_id` | One meal with its reading. |
| PUT | `/meals/{meal_id}` | `write:measurements` | `meal_id`, JSON `MealUpdate` (meal_type, eaten_at, description, price, vendor) | Change type, time or description, then read the meal again. |
| POST | `/meals/{meal_id}/analyze` | `write:measurements` | `meal_id` | Read the meal again with the current models. |
| GET | `/meals/{meal_id}/photo` | `read:all` | `meal_id` | The meal's photo (JPEG, EXIF removed). |

## Travail (heures d'embauche et de débauche)

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/work/clock` | `write:measurements` + ?token= | JSON `ClockIn` (kind, at) | Clock in or out (now unless ``at`` is given). |
| GET | `/work/export` | `read:all` | `start`?, `end`?, `level`?, `format`?, `contract_hours`? | Sessions, days, weeks or months as CSV, JSON or Excel. |
| GET | `/work/health` | `read:all` | `start`?, `end`?, `contract_hours`? | The work ↔ health file: days, sleep, legal landmarks, absences. |
| POST | `/work/import` | `write:measurements` + ?token= | `dry_run`?, form `file` | Import past clock-in / clock-out logs (txt, csv, json). |
| GET | `/work/incomplete` | `read:all` | — | Sessions with a missing half, each with the day's context. |
| GET | `/work/sessions` | `read:all` | `start`?, `end`? | Sessions between two days (default: the last 30), newest first. |
| POST | `/work/sessions` | `write:measurements` | JSON `WorkSessionIn` (start_at, end_at, note) | Add a session typed by hand (same start: that session is updated). |
| DELETE | `/work/sessions/{session_id}` | `write:measurements` | `session_id` | Delete a session. |
| PUT | `/work/sessions/{session_id}` | `write:measurements` | `session_id`, JSON `WorkSessionUpdate` (start_at, end_at, note) | Fix a session's times or note. |
| GET | `/work/stats` | `read:all` | `start`?, `end`?, `contract_hours`? | Totals, averages, overtime, weeks, months, 7/30/90/365 days. |

## Import d'historiques de Raccourcis

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/logs/import` | `write:measurements` + ?token= | `dry_run`?, form `files`, form `keys` | Import Shortcut logs: one time stamp per line, one kind per file. |

## Dossier travail : arrêts et absences

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/absences` | `read:all` | `start`?, `end`? | Absences overlapping two days (all by default), oldest first. |
| POST | `/absences` | Session / hub:full | JSON `AbsenceIn` (start_date, end_date, kind, cause, note) | Record an absence (arret_maladie, accident_travail, repos…). |
| POST | `/absences/import` | Session / hub:full | `dry_run`?, form `files`, form `person` | Import absences from an HR export (Lucca…: CSV, Excel, JSON). |
| DELETE | `/absences/{absence_id}` | Session / hub:full | `absence_id` | Delete an absence (its evidence stays). |
| PUT | `/absences/{absence_id}` | Session / hub:full | `absence_id`, JSON `AbsenceIn` (start_date, end_date, kind, cause, note) | Replace an absence's dates, kind, cause and note. |

## Dossier travail : preuves et traces

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/evidence` | `read:all` | `start`?, `end`? | Proofs and traces between two local days (default: all), oldest first. |
| POST | `/evidence` | Session / hub:full | form `file` | Add a proof or a trace (file optional): when, what, how many. |
| DELETE | `/evidence/{item_id}` | Session / hub:full | `item_id` | Delete an item and its file. |
| PUT | `/evidence/{item_id}` | Session / hub:full | `item_id`, JSON `EvidenceUpdate` (occurred_at, kind, title, description, count, absence_id, ended_at, place, amount, currency) | Fix an item's details (its file and fingerprint do not change). |
| GET | `/evidence/{item_id}/file` | `read:all` | `item_id` | The item's file, as received. |

## Sommeil : nuits, réveils, nuits saisies

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| GET | `/sleep/nights` | `read:all` | `start`?, `end`?, `missing`? | Nights by wake-up day, newest first (default: since the first one). |
| POST | `/sleep/nights` | Session / hub:full | JSON `TypedNight` (bedtime, wake_time, awakenings) | Type a night the watch missed (bedtime, wake-up, awakenings). |
| DELETE | `/sleep/nights/{night_id}` | Session / hub:full | `night_id` | Delete a night typed by hand. |
| GET | `/sleep/typed` | `read:all` | — | The nights typed by hand, newest first. |

## Autres

| Méthode | Route | Accès | Paramètres | Rôle |
|---|---|---|---|---|
| POST | `/traces/import` | Session / hub:full | `dry_run`?, `meals`?, form `files`, form `kinds`, form `person` | Import exports (CSV, Excel, JSON) and receipts (PDF, photo). |
