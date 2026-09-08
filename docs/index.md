# Phoenix Health Hub — documentation

- [Architecture](architecture.md) — services, request flow, roadmap.
- [Data model](data-model.md) — the fixed schema and the dynamic registry.
- Guides
  - [Add a metric](guides/add-a-metric.md) — a new field, no migration.
  - [Add a chart](guides/add-a-chart.md) — the governed chart component.
  - [Ingestion](guides/ingestion.md) — Apple Watch, CPAP, capture (Phase 3).
- [Architecture Decision Records](adr/) — the structural decisions.

The API is self‑documenting: OpenAPI 3.1 at `/api/v1/openapi.json`, Swagger
UI at `/api/v1/docs`, ReDoc at `/api/v1/redoc`.
