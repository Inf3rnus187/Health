"""Generate the API reference (``docs/api.md``) from the live routes.

Each route's access rule is read from its real dependencies, so the page
cannot drift from the code (a test compares it with the generated text).
Regenerate after changing a route::

    python -m app.cli.api_doc > ../docs/api.md
"""

from __future__ import annotations

import inspect
import sys
from collections.abc import Iterator
from typing import Any, get_args

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from pydantic import BaseModel

#: First path segment → section title.
SECTIONS = {
    "auth": "Authentification et 2FA",
    "me": "Compte",
    "tokens": "Jetons d'accès (API)",
    "summary": "Accueil",
    "catalog": "Catalogue des métriques",
    "metrics": "Métriques",
    "measurements": "Valeurs journalières",
    "samples": "Relevés bruts",
    "trends": "Tendances",
    "dashboard": "Tableaux de bord",
    "data": "Données (inventaire, réconciliation)",
    "events": "Événements",
    "ingest": "Ingestion (montre, PPC, photo)",
    "sync": "Synchro iPhone et Health Auto Export",
    "imports": "Import Apple Santé",
    "capture": "Capture",
    "workouts": "Séances, ECG, parcours",
    "ecg": "Séances, ECG, parcours",
    "routes": "Séances, ECG, parcours",
    "medical": "Dossier médical et documents",
    "biology": "Prises de sang (PDF)",
    "clinical": "Dossier CDA",
    "conditions": "Maladies",
    "treatments": "Traitements",
    "appointments": "Rendez-vous",
    "care": "Suivi",
    "evolution": "Évolution (marqueurs, poids, photos)",
    "photos": "Photos",
    "reports": "Rapports",
    "export": "Export",
    "automations": "Automatisations",
    "journal": "Journal (pipi, repas)",
    "meals": "Journal (pipi, repas)",
}
_INTRO = """# Référence de l'API

Généré depuis le code (`python -m app.cli.api_doc`) — ne pas éditer à la
main. Base : `/api/v1`. Documentation interactive : `/api/v1/docs`
(Swagger) et `/api/v1/redoc`.

**Accès** — *Public* : sans authentification. *Tout jeton* : session ou
n'importe quel jeton. *`scope`* : session, jeton `hub:full`, ou jeton
portant ce scope. *Session / hub:full* : connexion web ou jeton
`hub:full`. *Session uniquement* : connexion web (jamais un jeton).
Un jeton s'envoie en `Authorization: Bearer <jeton>` ; « + ?token= »
signale qu'il est aussi accepté en paramètre d'URL.
"""


def render(app: FastAPI) -> str:
    """The whole reference page as Markdown."""
    grouped: dict[str, list[APIRoute]] = {}
    for route in _routes(app):
        grouped.setdefault(_section(route.path), []).append(route)
    parts = [_INTRO]
    for title, routes in grouped.items():
        parts.append(f"\n## {title}\n")
        parts.append("| Méthode | Route | Accès | Paramètres | Rôle |")
        parts.append("|---|---|---|---|---|")
        parts.extend(_row(route) for route in routes)
    return "\n".join(parts) + "\n"


def main() -> None:
    """Print the reference (redirect it to ``docs/api.md``)."""
    from app.main import app

    sys.stdout.write(render(app))


def _routes(app: FastAPI) -> list[APIRoute]:
    """API routes in section order, then path order."""
    order = [*dict.fromkeys(SECTIONS.values()), "Autres"]
    routes = [
        r
        for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/api/v1/")
    ]
    return sorted(
        routes,
        key=lambda r: (order.index(_section(r.path)), r.path, _method(r)),
    )


def _section(path: str) -> str:
    """Section title of a route (by its first path segment)."""
    first = path.removeprefix("/api/v1/").split("/", 1)[0]
    return SECTIONS.get(first, "Autres")


def _method(route: APIRoute) -> str:
    """The route's HTTP method(s)."""
    return ", ".join(sorted(route.methods - {"HEAD"}))


def _row(route: APIRoute) -> str:
    """One table row."""
    doc = inspect.getdoc(route.endpoint) or route.summary or ""
    role = doc.splitlines()[0] if doc else ""
    cells = [
        _method(route),
        f"`{route.path.removeprefix('/api/v1')}`",
        _access(route.dependant),
        _params(route.dependant),
        role.replace("|", "\\|"),
    ]
    return "| " + " | ".join(cells) + " |"


def _access(dependant: Dependant) -> str:
    """The strictest access rule among the route's dependencies."""
    found = {_rule(dep) for dep in _walk(dependant)} - {None}
    for rule in ("Session uniquement", "Session / hub:full"):
        if rule in found:
            return rule
    scoped = sorted(r for r in found if r and r.startswith("`"))
    if scoped:
        return " ".join(scoped)
    return "Tout jeton" if "any" in found else "Public"


def _walk(dependant: Dependant) -> Iterator[Any]:
    """Every dependency callable, depth first."""
    for sub in dependant.dependencies:
        yield sub.call
        yield from _walk(sub)


def _rule(call: Any) -> str | None:
    """The access rule a dependency enforces (None when it enforces none)."""
    name = getattr(call, "__qualname__", "")
    if name == "get_interactive_principal":
        return "Session uniquement"
    if name == "get_user_principal":
        return "Session / hub:full"
    if name == "get_current_principal":
        return "any"
    scope = next(
        (
            cell.cell_contents
            for cell in getattr(call, "__closure__", None) or ()
            if isinstance(cell.cell_contents, str)
        ),
        None,
    )
    if scope is None or not name.startswith("require_scope"):
        return None
    flex = " + ?token=" if name.startswith("require_scope_flex") else ""
    return f"`{scope}`{flex}"


def _params(dependant: Dependant) -> str:
    """Path, query and body parameters, in short."""
    parts = [f"`{p.alias}`" for p in dependant.path_params]
    parts += [
        f"`{p.alias}`{'' if p.required else '?'}"
        for p in dependant.query_params
    ]
    parts += [_body(p) for p in dependant.body_params]
    return ", ".join(parts) or "—"


def _body(param: Any) -> str:
    """A body parameter: a JSON model (its fields) or a form field."""
    kind = param.field_info.annotation
    options = [a for a in get_args(kind) if a is not type(None)]
    optional = len(options) == 1
    if optional:  # Model | None: an optional JSON body
        kind = options[0]
    if inspect.isclass(kind) and issubclass(kind, BaseModel):
        fields = ", ".join(kind.model_fields)
        mark = "?" if optional else ""
        return f"JSON `{kind.__name__}`{mark} ({fields})"
    if param.alias == "body":
        return "JSON libre"
    return f"form `{param.alias}`"


if __name__ == "__main__":
    main()
