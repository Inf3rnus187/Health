# Guide — add a metric (no migration)

Adding a field is a **data** change: one row in `metric_definitions`. No
schema migration, no redeploy.

## Via the API

```bash
BASE=http://localhost:8080/api/v1
curl -s $BASE/metrics -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{
        "key": "mind.stress",
        "label": "Niveau de stress",
        "domain": "mind",
        "data_type": "score",
        "unit": "/10",
        "min_value": 0,
        "max_value": 10,
        "aggregation_hint": "avg"
      }'
```

Fields:

| Field | Notes |
|-------|-------|
| `key` | Unique, `domain.snake` (e.g. `mind.stress`). |
| `data_type` | `int·float·bool·enum·time·duration·text·score`. |
| `source` | `manual·watch·ppc·ai·script·derived` (default `manual`). |
| `enum_options` | Required list when `data_type = enum`. |
| `min_value` / `max_value` | Optional bounds; enforced on write. |
| `aggregation_hint` | `avg·sum·min·max·last`. |
| `formula` | For `derived` metrics (read‑only through the API). |

Record values immediately — the metric is live:

```bash
curl -s $BASE/measurements -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"metric_key":"mind.stress","date_key":"2026-01-15",
       "value":4}]}'
```

## Update or deactivate

```bash
curl -s -X PATCH $BASE/metrics/mind.stress \
  -H "Authorization: Bearer $ACCESS" -H 'Content-Type: application/json' \
  -d '{"label":"Stress ressenti","is_active":true}'
```

`key`, `data_type` and `domain` are immutable so existing measurements stay
valid; deactivating (`is_active:false`) hides a metric from writes while
keeping its history.

## Seeding new defaults

To ship a metric as a default, add an entry in
[`backend/app/seed/catalog.py`](../../backend/app/seed/catalog.py); the seed
step inserts any catalogue metric that does not yet exist (idempotent).
