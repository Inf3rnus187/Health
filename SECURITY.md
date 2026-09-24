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
- **MFA (optional)**: TOTP — `POST /auth/mfa/setup|enable|disable`; once
  enabled, login requires the `otp` code.
- **Media at rest (optional)**: set `MEDIA_ENCRYPTION_KEY` (Fernet) to
  transparently encrypt stored photos; served only via the authenticated
  endpoint.
- **RGPD**: `DELETE /api/v1/me` erases the account and all its data (DB
  cascade + media/export files); full export via `GET /export?format=json`;
  `RETENTION_DAYS` documents the retention policy.
- **Supply chain (CI)**: SBOM (syft), `pip-audit`, `pnpm audit`, and a
  Trivy filesystem scan run in the `Security` workflow; dependency versions
  are pinned with lockfiles (`uv.lock`, `pnpm-lock.yaml`).

## Planned (further hardening)

Signed & scanned container **images** (trivy/grype image scan + cosign
signing) at publish time, encrypted off‑site **backups**, and an automated
retention **purge** job.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the maintainers rather
than opening a public issue. Include steps to reproduce and affected
versions. We aim to acknowledge reports within a few days.
