# Contributing

Thanks for your interest in Phoenix Health Hub!

## Setup

```bash
# Backend
cd backend && uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Frontend
cd ../frontend && pnpm install

# Git hooks (runs the same gates as CI)
pipx install pre-commit && pre-commit install
```

## Quality gates (enforced by CI, non‑negotiable)

Structural limits (§14.1), checked by `tools/check_code_limits.py` and the
linters:

- ≤ 80 characters per line.
- ≤ 25 lines per function body.
- ≤ 5 public functions/methods per file.
- Cyclomatic complexity ≤ 10, nesting depth ≤ 3.
- One responsibility per module; docstrings on public modules/functions.

Run before pushing:

```bash
# Backend
cd backend
ruff check app tests && ruff format --check app tests
mypy app
python ../tools/check_code_limits.py app
pytest                      # coverage must stay ≥ 80%

# Frontend
cd ../frontend
pnpm typecheck && pnpm lint && pnpm format && pnpm build
```

## Conventions

- Python `snake_case`, TypeScript `camelCase`, classes/components
  `PascalCase`, metric keys `domain.snake`.
- No dead code; no untracked `TODO` (link an issue).
- Commit messages: imperative mood; reference an issue where relevant.
- New structural decisions get an ADR in `docs/adr`.

## Documentation (every commit)

A change is finished only when it is documented in the same commit —
see [CLAUDE.md](CLAUDE.md) « Documentation »: CHANGELOG.md, the French
user guide (web page and iPhone Shortcut), the API docstrings and
`docs/api.md`, the MCP tool and `docs/mcp-tools.md`, security and
configuration, the data model, the AI guide. The pre-commit hook
`docs-updated` (`tools/check_docs_updated.py`) refuses code without its
changelog and documentation.

## Pull requests

Keep changes focused and covered by tests. CI (lint → types → tests +
coverage → build → compose config) must be green before review.
