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
- **Transport**: the app speaks HTTP only internally; terminate TLS with your
  own reverse proxy.
- **Outbound calls**: none with personal data. The one lookup, Open
  Food Facts by barcode (`services/food_off.py`), is off by default
  (`FOOD_LOOKUP_ONLINE=false`); when enabled it sends the barcode only
  (no photo, account or meal) to `OPENFOODFACTS_URL`. A barcode on a
  photo (`POST /foods/scan`) is decoded on the hub, offline
  (`services/barcode_read.py`, zxing-cpp), and the photo is not kept.
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
- **Photo metadata**: meal and food photos are decoded and re-encoded as
  JPEG without EXIF (no GPS) before storage (`services/imaging.py`,
  `meal_photo.py`, `meal_extra.py`, `food_photos.py`). Body photos: the
  copy analysed and served is re-encoded the same way, but the original
  upload is also kept as received, EXIF included (encrypted when the key is
  set), and is served when normalising failed. **Proof files** (evidence)
  are kept byte for byte with their SHA-256 so a copy can be checked:
  their EXIF/GPS stays.
- **No token in the logs**: routes an iPhone Shortcut calls accept the
  token as `?token=` (below); the API access log (`core/logging.py`,
  `_NoTokens`) and nginx (`log_format no_token`) write `token=***`.
- **Updates without Docker access**: no container mounts `docker.sock`.
  `/system/update` (admin web session only) just drops a request file in
  `run/` (mounted at `/data/update`); the host's `update.sh`, run by the
  user's cron, does `git pull --ff-only` and the rebuild
  (`services/updates.py`, `update.sh`). The API never runs git or Docker.
- **RGPD**: `DELETE /api/v1/me` erases the account and its data (DB
  cascade + `MEDIA_DIR/<user>/` and `EXPORTS_DIR/<user>/`).
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
| **Web session** | `POST /auth/login` | Everything on the account's data. The **only** level for managing tokens (`/tokens`), MFA (`/auth/mfa/*`), deleting the account (`DELETE /me`) and downloading the pre-filled Shortcut (`GET /sync/shortcut`) — `InteractiveDep` in `core/deps.py`. |
| **Admin** | web session of an account with role `admin` (today: only the account created by the seed) | Also `GET`/`POST /system/update` — admin **web session** only, never a token (`AdminDep`, `core/deps_admin.py`). Also the shared metric catalogue, `POST /metrics` and `PATCH /metrics/{key}` — admin session, or an admin's token carrying `write:metrics` (or `hub:full`) (`CatalogDep`). |
| **`hub:full` token** | API token (MCP server, assistant) | What the web session does, **except** tokens, MFA, account deletion, the Shortcut download and `/system/update`; the catalogue only if its owner is admin. |
| **Scoped tokens** | API token with `ingest:watch`, `ingest:ppc`, `ingest:photo`, `write:measurements`, `write:metrics`, `read:all` | Only the routes carrying that scope. `ingest:*` send data. `write:measurements` sends, edits (meals, foods, work sessions) and **deletes by id** (measurements, meals and their photos, foods and their photos, pee entries, work sessions, medication doses). Reading health data needs `read:all`. `write:metrics` works for an admin only. |

The scope each route needs is listed in the [API reference](docs/api.md).

### Token in the URL (`?token=`)

For iPhone Shortcuts, these `write:measurements` routes also accept the
API token as a query parameter (`require_scope_flex`,
`core/deps_query.py`; an API token only, never a session JWT):
`POST /imports/apple-health`, `/sync/tally`, `/sync/auto-export`,
`/meals`, `/journal/urination`, `/logs/import`, `/work/import`,
`/work/clock`, `/medications/take`, `/treatments/{id}/intakes`,
`/foods/scan` (reads a barcode, saves nothing). Both
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
