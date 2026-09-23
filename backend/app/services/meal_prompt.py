"""Prompts of the meal reading (photo → foods; foods → nutrients)."""

from __future__ import annotations

import json
from typing import Any

_LOOK = """Tu es diététicien. Voici la photo d'un repas et ce que le patient \
en dit : « {description} ».
Liste les aliments présents et estime la quantité réellement servie de \
chacun, en grammes. La description du patient fait foi (quantités, \
cuisson, absence de matière grasse ou de sauce) ; la photo sert à \
estimer les portions et à repérer ce qu'il n'a pas cité.
Réponds uniquement en JSON :
{{"items": [{{"name": "aliment", "grams": 0, \
"preparation": "cru, grillé…"}}]}}"""

_NUTRITION = """Tu es diététicien et médecin nutritionniste. Analyse ce repas.
Repas : {meal} de {time}.
Description du patient (fait foi) : « {description} »
Aliments repérés sur la photo : {seen}
Maladies déclarées du patient : {conditions}

Pour chaque aliment, estime la quantité (g) puis ses nutriments à partir \
des valeurs de référence (table Ciqual) ramenées à cette quantité. \
Respecte la description : si elle dit sans huile, beurre, sauce ou \
graisse, n'en ajoute pas. N'invente aucun aliment absent de la \
description et de la photo.
Puis juge le repas pour CE patient (maladies ci-dessus) : note de 0 \
(à éviter) à 10 (idéal), un verdict en une phrase, les points positifs, \
les points à surveiller. Pas de posologie ni de prescription.
Réponds uniquement en JSON :
{{"items": [{{"name": "...", "grams": 0, "protein_g": 0, "carbs_g": 0, \
"sugars_g": 0, "fat_g": 0, "sat_fat_g": 0, "fiber_g": 0, \
"sodium_mg": 0}}], "score": 0, "verdict": "...", \
"positives": ["..."], "watch": ["..."]}}"""


def look(description: str) -> str:
    """The vision prompt: foods and portions on the photo."""
    return _LOOK.format(description=description or "(rien)")


def nutrition(context: dict[str, Any]) -> str:
    """The text-model prompt: nutrients per food and assessment."""
    seen = context.get("seen") or []
    return _NUTRITION.format(
        meal=context["meal"],
        time=context["time"],
        description=context.get("description") or "(aucune)",
        seen=json.dumps(seen, ensure_ascii=False) if seen else "(pas de photo)",
        conditions=", ".join(context.get("conditions") or []) or "aucune",
    )
