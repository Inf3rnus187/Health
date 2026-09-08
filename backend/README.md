# Phoenix Health Hub — Backend

FastAPI (async) service: authentication, the dynamic metric registry,
measurements/events, ingestion, photo pipeline, exports and reports.

See the repository [`README.md`](../README.md) for installation and the
[`docs/`](../docs) folder for architecture and developer guides.

## Local development

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv -e ".[dev]"
source .venv/bin/activate
ruff check . && mypy app && pytest
```
