"""Generate the MCP tool reference (``docs/mcp-tools.md``) from the server.

Regenerate after adding or changing a tool::

    python -m phoenix_mcp.doc > ../docs/mcp-tools.md
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from types import ModuleType
from typing import Any

from phoenix_mcp import (
    tools_body,
    tools_data,
    tools_journal,
    tools_record,
    tools_reports,
)
from phoenix_mcp.app import mcp

#: Tool module → section title, in reading order.
SECTIONS: tuple[tuple[ModuleType, str], ...] = (
    (tools_data, "Données et métriques"),
    (tools_record, "Dossier médical, Suivi, documents"),
    (tools_journal, "Journal : pipi et repas"),
    (tools_body, "Évolution, photos, données Apple"),
    (tools_reports, "Rapports, automatisations, accès direct"),
)
_INTRO = """# Outils du serveur MCP

Généré depuis le serveur (`python -m phoenix_mcp.doc`) — ne pas éditer à
la main. Chaque outil appelle l'API REST avec le jeton `hub:full` ;
configuration et connexion d'un client : [guide MCP](guides/mcp.md).
Paramètre suivi de `*` : obligatoire ; sinon la valeur par défaut est
indiquée.
"""


async def render() -> str:
    """The whole reference page as Markdown."""
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    parts = [_INTRO, f"{len(tools)} outils.\n"]
    for module, title in SECTIONS:
        parts.append(f"## {title}\n")
        for name in _names(module):
            parts.append(_tool(tools[name]))
    return "\n".join(parts)


def main() -> None:
    """Print the reference (redirect it to ``docs/mcp-tools.md``)."""
    sys.stdout.write(asyncio.run(render()))


def _names(module: ModuleType) -> list[str]:
    """Tools defined in a module, in definition order."""
    return [
        name
        for name, obj in vars(module).items()
        if inspect.iscoroutinefunction(obj)
        and obj.__module__ == module.__name__
    ]


def _tool(tool: Any) -> str:
    """One tool: name, description, parameters."""
    doc = inspect.cleandoc(tool.description or "")
    params = _params(tool.inputSchema)
    lines = [f"### `{tool.name}`\n", doc, ""]
    if params:
        lines.append(f"Paramètres : {params}\n")
    return "\n".join(lines)


def _params(schema: dict[str, Any]) -> str:
    """Parameters with their type and default (``*`` = required)."""
    required = set(schema.get("required", []))
    out = []
    for name, prop in schema.get("properties", {}).items():
        kind = _type(prop)
        if name in required:
            out.append(f"`{name}`* ({kind})")
        else:
            out.append(f"`{name}` ({kind}, défaut `{prop.get('default')}`)")
    return ", ".join(out)


def _type(prop: dict[str, Any]) -> str:
    """A JSON-schema type in short (``string | null``)."""
    kinds = [p.get("type", "any") for p in prop.get("anyOf", [prop])]
    return " | ".join(str(k) for k in kinds)


if __name__ == "__main__":
    main()
