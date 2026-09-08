# ADR 0005 — Security hardening choices

- Status: accepted
- Date: 2026-03

## Context

§12/§12.1 require defense-in-depth for sensitive health data and media,
including optional MFA, at-rest media encryption, RGPD erasure, and
supply-chain scanning.

## Decision

- **MFA**: optional TOTP (`pyotp`). A secret is assigned at `setup`, enabled
  only after a verified code; when enabled, `authenticate` requires the code.
  Stored as `users.mfa_secret` / `mfa_enabled` (migration `0003`).
- **At-rest media encryption**: optional, application-level Fernet
  (`MEDIA_ENCRYPTION_KEY`). All media reads/writes go through
  `app.core.crypto`, so encryption is transparent and off by default (a
  passthrough). Chosen over volume encryption so it is portable and
  per-deployment configurable.
- **RGPD erasure**: `DELETE /me` deletes the user; `ON DELETE CASCADE`
  removes all owned rows, and the user's media/export directories are purged.
  Full data export reuses the tidy JSON export.
- **Supply chain**: gitleaks (pre-commit + CI, blocking), plus informational
  `pip-audit`, `pnpm audit`, Trivy fs scan and a syft SBOM artifact in a
  dedicated CI workflow. Dependency scans are informational so upstream
  advisories don't block delivery while still being surfaced.

## Consequences

- Encryption and MFA add no burden when unused (both opt-in), and are covered
  by unit/integration tests.
- Image signing (cosign) and encrypted backups remain follow-ups; they need a
  registry and backup destination that are deployment-specific.
