"""French names of every metric domain (dashboard tabs, MCP, reports).

Apple Health domains come from the HealthKit catalog; the hub's own
domains (PPC, habits such as cigarettes, lab results…) are added here so
every page names a domain the same way.
"""

from __future__ import annotations

from app.services.apple_health import hk_catalog

_HUB = {
    "bio": "Biologie",
    "liver": "Foie (FibroScan)",
    "elimination": "Élimination (urine)",
    "profile": "Profil",
    "vitals": "Signes vitaux",
    "fitness": "Forme physique",
    "rest": "Repos et récupération",
    "ppc": "PPC (apnée du sommeil)",
    "workout": "Séances",
    "walk": "Marche",
    "habit": "Habitudes (tabac, café…)",
    "work": "Travail (heures)",
    "state": "État et ressenti",
    "food": "Alimentation",
    "hydration": "Hydratation",
    "water": "Eau",
    "med": "Médicaments",
    "nap": "Siestes",
    "photo": "Photos",
    "ai": "Analyses IA",
    "context": "Contexte",
    "apple": "Autres données Apple",
}

#: Domain code → French label.
LABELS: dict[str, str] = {**hk_catalog.DOMAINS, **_HUB}


def label(domain: str) -> str:
    """The French name of a domain (its code when unknown)."""
    return LABELS.get(domain, domain)
