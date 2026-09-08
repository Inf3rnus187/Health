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
- **Audit**: every write is recorded in `audit_log`.
- **Secrets**: never committed; injected via `.env`; `.env` is git‑ignored
  and `install.sh` generates a strong `SECRET_KEY`.
- **Transport**: the app speaks HTTP only internally; terminate TLS with your
  own reverse proxy.

## Planned (Phase 9 hardening)

MFA (optional), gitleaks in pre‑commit/CI, SBOM (syft), dependency and image
scanning (pip‑audit/npm‑audit, trivy/grype), signed images (cosign),
at‑rest media encryption, configurable retention and encrypted backups.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the maintainers rather
than opening a public issue. Include steps to reproduce and affected
versions. We aim to acknowledge reports within a few days.
