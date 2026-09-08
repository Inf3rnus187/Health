# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Ingestion (Phase 3)**: `POST /ingest/watch` and `POST /ingest/ppc`
  accept generic samples keyed by `metric_key` or by an external
  `healthkit_type`, resolved through a **configurable mapping table**
  (`ingest_mappings`) so new fields are absorbed with no code change;
  unresolved keys are reported, not fatal.
- Mapping management: `GET/POST /ingest/mappings`; seeded global HealthKit
  defaults.
- **Mode B** `POST /capture`: opens a `capture_session` event, records
  weight + photo flags, pre‑fills the latest Watch/CPAP data and returns the
  manual‑only complement form.
- Alembic migration `0002_ingest_mappings` (incremental, per‑table from the
  ORM metadata).

## [0.1.0] — 2026-01

Foundation milestone (specification Phases 1–2).

### Added

- Docker Compose stack: `db` (PostgreSQL 16), `redis`, `api` (FastAPI),
  `worker` (ARQ), `web` (Nginx + React build), optional `mcp`.
- One‑shot `install.sh` bootstrap (build, migrate, seed, admin) and a fully
  commented `.env.example`.
- Authentication: argon2id passwords, JWT access tokens, **rotating and
  revocable** refresh sessions, `/auth/{login,refresh,logout,me}`.
- Scoped, hashed **API tokens** with CRUD and scope enforcement.
- **Dynamic metric registry** (`/metrics`) — add a field at runtime with no
  migration.
- **Measurements**: idempotent batch write, filtered reads, rolling
  aggregation series; **events** with attached measurements.
- Polymorphic typed measurement storage; partial unique indexes for zero
  redundancy; derived metrics marked read‑only.
- Seeded metric **catalogue** (Annexe A, 76 metrics) + initial admin.
- Append‑only **audit log** of every write.
- Alembic initial migration driven by the ORM metadata.
- React (Vite + TS) front: login, token/auth flow (TanStack Query), metric
  catalogue, a governed chart component with a semantic palette, quick weight
  entry.
- Quality tooling: ruff, mypy (strict), ESLint + Prettier, a custom
  structural‑limits checker, pre‑commit config, and GitHub Actions CI with a
  ≥ 80 % coverage gate.
- Documentation: README, architecture and data‑model docs (Mermaid), how‑to
  guides, and ADRs.

### Security

- Security headers + strict CSP (web tier), restricted CORS, non‑root
  hardened container images.

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/v0.1.0
