# Phoenix Health Hub — documentation

- Guides (français)
  - [Configuration](guides/configuration.md) — installer, mettre à jour,
    variables, jetons et scopes, services, journaux.
  - [Utilisation](guides/utilisation.md) — chaque page et les parcours types.
  - [IA médicale](guides/ia-medicale.md) — MedGemma, lecture des documents,
    synthèse clinique, méthode photo, dépannage.
  - [MCP](guides/mcp.md) — brancher un assistant sur le hub.
  - [Multi-utilisateur](multi-utilisateur.md) — analyse complète (données,
    rôles, scopes API/MCP/raccourcis, pages Mon compte et Admin) et plan.
- Guides (developer)
  - [Ingestion](guides/ingestion.md) — Apple Health, Health Auto Export,
    Shortcuts, watch, CPAP, photos.
  - [Add a metric](guides/add-a-metric.md) — a new field, no migration.
  - [Add a chart](guides/add-a-chart.md) — the governed chart component.
- References (generated from the code)
  - [API](api.md) — every route, its parameters and required access.
  - [MCP tools](mcp-tools.md) — every tool and its parameters.
- [Architecture](architecture.md) — services, request flow, roadmap.
- [Data model](data-model.md) — the fixed schema and the dynamic registry.
- [Architecture Decision Records](adr/) — the structural decisions.
- [CLAUDE.md](../CLAUDE.md) — the rules for every change: privacy,
  isolation, and the documents each commit must update.

The API is also self‑documenting: OpenAPI 3.1 at `/api/v1/openapi.json`,
Swagger UI at `/api/v1/docs`, ReDoc at `/api/v1/redoc`.
