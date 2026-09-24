# Working on Phoenix Health Hub

Rules for anyone changing this repository — a person or an AI
assistant. They apply to **every commit**, without being asked.

## Data and privacy

- Health data never leaves the hub: no call to an outside service with
  personal data. An outbound lookup (e.g. Open Food Facts by barcode) is
  opt-in, sends the minimum (the barcode only) and is documented.
- Never commit `.env`, a database, media, exports, or any real personal
  file. Tests and docs use fake identities only (`test.user@example.com`,
  « Traitement A », « Marque test ») — never a real person's name, town or
  card number.
- Every query is scoped to its user; an object of another user answers
  404. A new route gets a two-account test (`member` fixture).

## Documentation — part of every change

A feature is not done until it is documented **in the same commit**:

1. **CHANGELOG.md** — what changed, for whom, under Added / Fixed /
   Security.
2. **The user guide** (`docs/guides/utilisation.md`, in French): the page,
   tab, button and what it does; the **iPhone Shortcut** recipe when the
   feature can be used from one (URL, method, fields, token scope).
3. **API**: docstrings on each route (they generate `docs/api.md`:
   `SECRET_KEY=doc-generation-only-0123456789abcdef python -m
   app.cli.api_doc > ../docs/api.md` from `backend/`); new routes also in
   `docs/guides/ingestion.md` when a device or Shortcut calls them.
4. **MCP**: a tool for every user feature (`mcp/phoenix_mcp/tools_*.py`,
   in `doc.py`'s sections), then `python -m phoenix_mcp.doc >
   ../docs/mcp-tools.md` from `mcp/`, and `docs/guides/mcp.md`.
5. **Security**: any change of access, scope, token, log, file storage or
   outbound call goes in `SECURITY.md` and `docs/guides/configuration.md`
   (with its environment variable, if any, also in `.env.example`).
6. **Data model**: a new table or column goes in `docs/data-model.md`
   with its migration (`backend/alembic/versions`, guarded, ADR-0004).
7. **AI**: a change of what a model reads or answers goes in
   `docs/guides/ia-medicale.md`.

The pre-commit hook `docs-updated` refuses a commit that changes code
without CHANGELOG.md and a hand-written document.

## Gates before every push

```bash
cd backend
uvx ruff@0.7.4 check app tests && uvx ruff@0.7.4 format --check app tests
.venv/bin/python -m mypy app
.venv/bin/python ../tools/check_code_limits.py app   # ≤ 5 public / file, ≤ 25-line bodies
.venv/bin/python -m pytest -q
cd ../mcp && uvx ruff@0.7.4 check phoenix_mcp tests && .venv/bin/python -m mypy phoenix_mcp && .venv/bin/python -m pytest -q
cd ../frontend && npx prettier --check src && npx eslint src --max-warnings 0 && npx tsc --noEmit -p . && npm run build
```

A web change is also checked in a browser (phone width 390 px and
desktop) with fake data.
