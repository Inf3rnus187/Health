"""Refuse a commit that changes the product without saying so.

Run by pre-commit on the staged files. When application code changes
(backend/app, backend/alembic, frontend/src, mcp/phoenix_mcp, nginx,
docker-compose.yml, update.sh, install.sh), the same commit must also
change CHANGELOG.md and at least one hand-written document (README.md,
SECURITY.md, docs/…, excluding the generated references docs/api.md and
docs/mcp-tools.md). A pure test, tooling or documentation change passes.

Bypass on purpose only (a formatting-only change): ``SKIP=docs-updated``.
"""

from __future__ import annotations

import subprocess
import sys

_CODE = (
    "backend/app/",
    "backend/alembic/",
    "frontend/src/",
    "mcp/phoenix_mcp/",
    "nginx/",
    "docker-compose.yml",
    "update.sh",
    "install.sh",
)
_GENERATED = ("docs/api.md", "docs/mcp-tools.md")


def _staged() -> list[str]:
    """The paths staged for the commit."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def _is_doc(path: str) -> bool:
    """A hand-written document."""
    if path in _GENERATED:
        return False
    return path in ("README.md", "SECURITY.md") or (
        path.startswith("docs/") and path.endswith(".md")
    )


def main() -> int:
    """0 when the commit documents its code change, else 1."""
    staged = _staged()
    code = [p for p in staged if p.startswith(_CODE)]
    if not code:
        return 0
    missing = []
    if "CHANGELOG.md" not in staged:
        missing.append("CHANGELOG.md")
    if not any(_is_doc(p) for p in staged):
        missing.append("a guide in docs/ (or README.md / SECURITY.md)")
    if not missing:
        return 0
    print("Code changed without its documentation: " + ", ".join(missing))
    print("Changed code: " + ", ".join(code[:8]))
    print("Document the feature, its security, its use (web, iPhone")
    print("Shortcut, API, MCP) — see CLAUDE.md « Documentation ».")
    return 1


if __name__ == "__main__":
    sys.exit(main())
