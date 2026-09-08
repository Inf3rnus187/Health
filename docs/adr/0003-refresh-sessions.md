# ADR 0003 — Refresh sessions table for rotation & revocation

- Status: accepted
- Date: 2026-01

## Context

Security requires short access JWTs plus a **rotating**, **revocable**
refresh token (§12, §12.1). Stateless refresh tokens cannot be revoked
before expiry, and cannot be rotated with old‑token invalidation.

## Decision

Add an `auth_sessions` table (beyond the §5.2 list) holding one row per
login: `id` (the refresh `sid`), `user_id`, `revoked`, `expires_at`,
`last_used_at`.

- **Login** opens a session; the refresh JWT carries its `sid`.
- **Refresh** validates the session, revokes it, opens a new one, and issues
  a new pair (rotation with old‑token invalidation).
- **Logout** revokes the session.

Access tokens stay stateless and short (default 15 min); they are not checked
against the table on every request.

## Consequences

- Refresh tokens are revocable and single‑use; reuse of a rotated token is
  rejected (tested).
- One extra table, justified by the security requirement; documented here as
  an addition to the specified schema.
- A revoked login still allows access for up to the access‑token TTL; this is
  the standard trade‑off and is acceptable at 15 minutes.
