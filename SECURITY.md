# Security policy

Phoenix Health Hub stores sensitive health data (including torso photos), so
security is a first‑class concern (§12).

## Implemented today

- **Passwords**: argon2id hashing.
- **Sessions**: short access JWTs + rotating, revocable refresh sessions.
- **Machine access**: scoped API tokens, stored only as SHA‑256 digests,
  revocable and expirable.
- **Isolation**: every query is scoped to the authenticated `user_id`.
- **Validation**: strict Pydantic schemas on all input.
- **Headers**: `X‑Content‑Type‑Options`, `X‑Frame‑Options`,
  `Referrer‑Policy` on the API; a strict CSP + these on the web tier.
- **CORS**: disabled by default; explicit allow‑list via `CORS_ORIGINS`.
- **Audit**: every write is recorded in `audit_log` — counter taps with
  the day they count for and their channel (site / Shortcut token),
  medication doses, and each report generated with its SHA-256.
- **Report authenticity**: each report file's SHA-256 is stored on the
  report and in the audit log; `POST /reports/verify` (web « Vérifier un
  fichier ») tells whether a copy is byte-for-byte one of the caller's
  reports. Every PDF page carries the report id, the generation time and
  zone; the header shows the version running and the SHA-256 of the data
  it was built on.
- **Secrets**: never committed; injected via `.env`; `.env` is git‑ignored
  and `install.sh` generates a strong `SECRET_KEY`. **gitleaks** runs in
  pre‑commit and CI.
- **Bounded work in the worker**: a reconcile runs its metrics in
  `RECONCILE_PARALLEL` processes of its own (`python -m
  app.cli.rollup_worker`, same user, same environment, one database
  connection each, stopped with it or killed on an error). One reconcile
  at a time has processes in a worker: accounts importing or reconciling
  together wait their turn, so they cannot multiply processes and
  connections (10 jobs × 4 processes would have come near PostgreSQL's
  100 connections). A reconcile waiting its turn holds no transaction.
- **Transport**: the app speaks HTTP only internally; terminate TLS with your
  own reverse proxy.
- **Outbound calls**: none with personal data. The one lookup, Open
  Food Facts by barcode (`services/food_off.py`), is off by default
  (`FOOD_LOOKUP_ONLINE=false`); when enabled it sends the barcode only
  (no photo, account or meal) to `OPENFOODFACTS_URL` — when the user asks
(a lookup, « ↻ Open Food Facts », « Tout relire ») and, unless
`FOOD_REFRESH_DAYS=0`, by the worker each night for sheets whose page
is older than that many days (at most 50 a night, one second apart).
Over time Open Food Facts can thus see which barcodes the hub's address
asks for, never who eats them. A barcode on a
  photo (`POST /foods/scan`) is decoded on the hub, offline
  (`services/barcode_read.py`, zxing-cpp), and the photo is not kept.
- **Explanation links**: « Comprendre ces références » under a meal,
  and a sheet's Open Food Facts details, hold plain links (EU
  regulation, ANSES, WHO, Santé.fr, Open Food Facts, Ciqual). The hub
  calls none of them; the browser opens one in a new tab only when it
  is tapped, with `rel="noreferrer noopener"` (no hub address sent), and
  no address carries personal data — a product link carries its barcode
  only. The official references a meal is set against are constants of
  the code (`services/meal_reference.py`), read offline.
- **MFA (optional, no web screen yet)**: TOTP —
  `POST /auth/mfa/setup|enable|disable`, called with a web session's
  access token (never an API token); once enabled, `POST /auth/login`
  requires the `otp` code. The web login form has no code field: see
  [Known limitations](#known-limitations).
- **Files at rest (optional)**: set `MEDIA_ENCRYPTION_KEY` (Fernet) and
  every file written under `MEDIA_DIR` is encrypted: body photos, meal
  photos (plate and extra photos), food photos, medical documents, proof
  files, ECG traces (CSV), GPS routes (GPX) and the Apple CDA document
  (`services/photo_storage.py`, `medical.py`, `evidence_files.py`,
  `apple_health/blobs.py`, `clinical.py`). Files are served decrypted only
  by authenticated endpoints. **Not encrypted**: generated reports and
  exports (`EXPORTS_DIR/<user>/`, `services/reports.py`), uploaded Apple
  Health exports kept in `EXPORTS_DIR/imports/`, the upload spool
  (`TMPDIR=/data/exports/tmp`) and the PostgreSQL database itself (values,
  notes, AI readings). Losing the key makes the encrypted files
  unreadable for good.
- **nginx writes no body sent to disk**: what a page, a Shortcut or an
  app sends through `/api/` (meal photos, documents, Health Auto
  Export's JSON…) is streamed to the API as it arrives
  (`proxy_request_buffering off`, `nginx/default.conf.template`); it
  used to sit unencrypted in a temporary file of the `web` container
  (`client_temp`) until the API had it. Answers over 2 MB (an export, a
  report, a large decrypted photo; `WEB_PROXY_BUFFERS` ×
  `WEB_PROXY_BUFFER_KB`) still spill briefly to nginx's `proxy_temp`,
  inside the container, never on a volume.
- **Every size and time limit is the operator's** (`.env`,
  docs/guides/configuration.md, « Réglages de fonctionnement »): a
  request through nginx is capped at `WEB_MAX_BODY_MB` (32 MB; it was a
  fixed 25 MB, below the 30 MB a proof may weigh), each file by its own
  limit (`MAX_UPLOAD_MB`, `MEDICAL_MAX_MB`, `EVIDENCE_MAX_MB`). Raising
  them lets larger bodies reach the API; a value out of bounds stops the
  API at start with the variable named. nginx's template is filled with
  the `WEB_…` variables only (`NGINX_ENVSUBST_FILTER`): no other
  variable of the container reaches its configuration.
- **Compression never touches a secret**: nginx gzips text (the page's
  code, the API's JSON) except the answers that carry a session or a
  token — `/api/v1/auth/…`, `/api/v1/tokens`, `/api/v1/sync/shortcut` —
  so the size of a compressed answer cannot leak one (BREACH).
- **The API's address is asked again**: nginx resolves `api` through
  Docker's DNS every 10 s (`resolver 127.0.0.11`), so a rebuilt API
  container is reached at its new address; it never falls back to
  anything outside the compose network.
- **A request keeps the metrics it read** (`services/metric_memo.py`):
  the definitions of the shared catalogue only (no user data), for that
  request's database session; forgotten on rollback or when metrics are
  deleted.
- **Photo metadata**: meal and food photos are decoded and re-encoded as
  JPEG without EXIF (no GPS) before storage (`services/imaging.py`,
  `meal_photo.py`, `meal_extra.py`, `food_photos.py`). Body photos: the
  copy analysed and served is re-encoded the same way, but the original
  upload is also kept as received, EXIF included (encrypted when the key is
  set), and is served when normalising failed. **Proof files** (evidence)
  are kept byte for byte with their SHA-256 so a copy can be checked:
  their EXIF/GPS stays.
- **No token in the logs**: routes an iPhone Shortcut calls accept the
  token as `?token=` (below); the API access log (`core/access_log.py`,
  which replaces uvicorn's line) and nginx (`log_format no_token`) write
  `token=***`. The API line holds the UTC time, the client address nginx
  saw (`X-Real-IP`: an address of your network), the request line, the
  status and the duration — never a header, a body or a token.
- **An unreachable hub never logs out**: while the API restarts (an
  update), the web page keeps its refresh token and tries again every
  5 s; only a refresh the hub refuses (401) signs out.
- **Updates without Docker access**: no container mounts `docker.sock`.
  `/system/update` (admin web session only) just drops a request file in
  `run/` (mounted at `/data/update`); the host's `update.sh`, run by the
  user's cron, does `git pull --ff-only` and the rebuild
  (`services/updates.py`, `update.sh`). The API never runs git or Docker.
- **RGPD**: `DELETE /api/v1/me` erases the account and its data (DB
  cascade + `MEDIA_DIR/<user>/` and `EXPORTS_DIR/<user>/`). The raw
  samples' counts (`sample_counts`, the inventory) go with the samples:
  the database's triggers remove them as the cascade deletes the
  samples (tested on PostgreSQL).
  `GET /export?format=csv|json|xlsx|fhir` exports the **daily values
  only** (`measurements`: date, metric, value, unit, source —
  `services/export.py`): not the raw samples, documents, photos, meals,
  journal, work sessions or proofs. There is no full-account export yet
  (see [backups](README.md#data-backup--restore)). `RETENTION_DAYS`
  documents the retention policy (no purge job).
- **Supply chain (CI)**: SBOM (syft), `pip-audit`, `pnpm audit`, and a
  Trivy filesystem scan run in the `Security` workflow; dependency versions
  are pinned with lockfiles (`uv.lock`, `pnpm-lock.yaml`).

## Access levels

A web login gives an access JWT (`ACCESS_TOKEN_TTL_MIN`, 15 min) and a
refresh token; an API token is a long random secret created in the web
app, stored as a SHA‑256 digest. Every level only reaches its own
account's data; the metric catalogue is the one thing shared, hence
admin-only writes.

| Level | How | May |
|-------|-----|-----|
| **Anyone** | no sign-in | `GET /health` (up or not) and `GET /system/settings`: the web page's timings and form limits from the environment (retries, polls, « Par page » choices, photos per meal, longest analysis delay, weekly work maximum) — no secret, nothing of an account, read before the login page. |
| **Web session** | `POST /auth/login` | Everything on the account's data. The **only** level for managing tokens (`/tokens`), MFA (`/auth/mfa/*`), deleting the account (`DELETE /me`) and downloading the pre-filled Shortcut (`GET /sync/shortcut`) — `InteractiveDep` in `core/deps.py`. |
| **Admin** | web session of an account with role `admin` (today: only the account created by the seed) | Also `GET`/`POST /system/update` — admin **web session** only, never a token (`AdminDep`, `core/deps_admin.py`). Also the shared metric catalogue, `POST /metrics` and `PATCH /metrics/{key}` — admin session, or an admin's token carrying `write:metrics` (or `hub:full`) (`CatalogDep`). |
| **`hub:full` token** | API token (MCP server, assistant) | What the web session does, **except** tokens, MFA, account deletion, the Shortcut download and `/system/update`; the catalogue only if its owner is admin. |
| **Scoped tokens** | API token with `ingest:watch`, `ingest:ppc`, `ingest:photo`, `write:measurements`, `write:metrics`, `read:all` | Only the routes carrying that scope. `ingest:*` send data. `write:measurements` sends, edits (meals, foods, work sessions) and **deletes by id** (measurements, meals and their photos, foods and their photos, pee entries, work sessions, medication doses). Reading health data needs `read:all`. `write:metrics` works for an admin only. |

The scope each route needs is listed in the [API reference](docs/api.md).

**iPhone app sync** (`POST /sync/healthkit`, `GET /sync/healthkit`):
a `write:measurements` token sent **in the `Authorization` header
only** — never `?token=` (an app has no reason to put it in a URL). It
writes, replaces and deletes only its owner's rows of the `healthkit`
channel, by HealthKit UUID (unique per user: another account's UUIDs are
never reached), and each sync is audited (`sync` / `healthkit`: the
counts, and since 1 October 2026 the refused lines as type, reason and
count, the milliseconds of each step (`ms`, step names and metric
keys) and the commit running — never a value, a date of a sample or a
UUID). The same counts and times go to the API log (`healthkit_synced`,
with the user id). `./version.sh` on the host only reads (git, the
containers' `GIT_COMMIT`, the database's migration). The status adds
up the owner's own audited refusals of the last `SYNC_REFUSED_DAYS`
days; another account's syncs are never read. Nothing leaves the hub.

### Token in the URL (`?token=`)

For iPhone Shortcuts, these `write:measurements` routes also accept the
API token as a query parameter (`require_scope_flex`,
`core/deps_query.py`; an API token only, never a session JWT):
`POST /imports/apple-health`, `/sync/tally`, `/sync/auto-export`,
`/meals`, `/journal/urination`, `/logs/import`, `/work/import`,
`/work/clock`, `/medications/take`, `/treatments/{id}/intakes`,
`/foods/scan` (reads a barcode, saves nothing), `/stock` (a purchase
scanned). Both
access logs write `token=***`, but a URL can still end up in a proxy you
add in front, a browser history or a Shortcut shared with someone: give
such a token `write:measurements` only, and revoke it if it leaks.

### MCP server

- Each network request carries the caller's own token, checked against
  `GET /auth/scopes`: a `hub:full` token (a web session's access JWT also
  passes); anything else gets 401 / 403. The answer is cached **60 s**
  per token (`mcp/phoenix_mcp/auth.py`): a revoked token keeps working
  for up to a minute.
- Tools only call API paths relative to `/api/v1`: a full URL, `//host`,
  a `..` segment or a backslash is refused before any request
  (`_api_path`, `mcp/phoenix_mcp/client.py`), so the token never leaves
  for another host.
- The MCP port is published on `MCP_BIND` (default `127.0.0.1`) — not
  behind nginx.

## Known limitations

The full analysis and plan are in
[docs/multi-utilisateur.md](docs/multi-utilisateur.md).

- **MFA locks you out of the web app**: the login form
  (`frontend/src/components/LoginForm.tsx`) has no code field and there
  is no setup screen; once MFA is enabled, only an API client sending
  `otp` can log in. Do not enable it on the account you use in the
  browser.
- **No login rate limit** (API and nginx): nothing slows down password
  guessing — keep the hub on a private network or behind a proxy that
  limits it.
- **Logout does not end the access JWT**: it revokes the refresh session,
  but the access token stays valid until it expires (15 min by default);
  the session id (`sid`) is not checked per request (`core/deps.py`).
- **Refresh token in `localStorage`** (`phoenix.refresh`,
  `frontend/src/api/client.ts`): readable by any script running on the
  page (the strict CSP limits that).
- **No password change**: no route changes a password; `ADMIN_PASSWORD`
  is read only when the admin account is created.
- **Example secrets are accepted**: the example `ADMIN_PASSWORD`,
  `POSTGRES_PASSWORD` and `SECRET_KEY` of `.env.example` pass validation
  (`install.sh` replaces only `SECRET_KEY`).
- **Single account in practice**: only the seeded admin exists; no route
  or page creates another account or changes a role.
- **The `mcp` container receives the whole `.env`** (`env_file` in
  `docker-compose.yml`): `SECRET_KEY`, database password,
  `MEDIA_ENCRYPTION_KEY`… although it only needs `API_BASE_URL` and its
  transport settings.
- **Unencrypted files**: reports, exports, uploaded Apple exports and the
  upload spool (see *Files at rest*). Uploaded Apple exports
  (`EXPORTS_DIR/imports/`) are not deleted after the import, nor by
  `DELETE /me`.
- **`run/` is writable by all** (`1777`, so the API's uid can drop a
  request): a host user can ask for an update too. It only installs what
  the tracked branch holds (fast-forward); with `update.sh --auto`, any
  new commit on that branch is installed without a click.

## Planned (further hardening)

Signed & scanned container **images** (trivy/grype image scan + cosign
signing) at publish time, encrypted off‑site **backups**, and an automated
retention **purge** job.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the maintainers rather
than opening a public issue. Include steps to reproduce and affected
versions. We aim to acknowledge reports within a few days.
