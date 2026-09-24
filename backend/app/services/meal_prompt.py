"""Prompts of the meal reading (photo → foods; foods → nutrients)."""

from __future__ import annotations

import json
from typing import Any

_LOOK = """Tu es diététicien. Voici {photos} d'un repas et ce que le \
patient en dit : « {description} ».
Liste les aliments présents et estime la quantité réellement servie de \
chacun, en grammes. La description du patient fait foi (quantités, \
cuisson, absence de matière grasse ou de sauce) ; la photo sert à \
estimer les portions et à repérer ce qu'il n'a pas cité.{labels}
Réponds uniquement en JSON :
{{"items": [{{"name": "aliment", "grams": 0, \
"preparation": "cru, grillé…"}}], "labels": [{{"name": "produit", \
"net_g": 0, "per_100g": {{"energy_kcal": 0, "protein_g": 0, \
"carbs_g": 0, "sugars_g": 0, "fat_g": 0, "sat_fat_g": 0, "fiber_g": 0, \
"sodium_mg": 0}}}}]}}"""
_LABELS = """
Certaines photos montrent un emballage ou un tableau de valeurs \
nutritionnelles : relève-les exactement dans "labels" (nom du produit, \
poids net, valeurs pour 100 g ; null si illisible)."""

_NUTRITION = """Tu es diététicien et médecin nutritionniste. Analyse ce repas.
Repas : {meal} de {time}.
Description du patient (fait foi) : « {description} »
Aliments repérés sur la photo : {seen}
{foods}{refs}Maladies déclarées du patient : {conditions}

Pour chaque aliment, estime la quantité (g) — une quantité donnée \
ci-dessus pour un produit fait foi — puis ses nutriments ramenés à \
cette quantité. Pour un produit dont l'étiquette est donnée ci-dessus, \
utilise ses valeurs (elles font foi : n'écris pas qu'il faudrait \
vérifier sa composition) et rends son "food_id". Pour les autres, \
choisis dans la liste Ciqual la référence la plus proche (même aliment, \
même cuisson ou préparation) et rends son code dans "ciqual" (null si \
aucune ne convient) : ses valeurs seront celles de la table. \
Respecte la description : si elle dit sans huile, beurre, sauce ou \
graisse, n'en ajoute pas. N'invente aucun aliment absent de la \
description et de la photo.
Puis juge le repas pour CE patient (maladies ci-dessus) : note de 0 \
(à éviter) à 10 (idéal), un verdict en une phrase, les points positifs, \
les points à surveiller. Pas de posologie ni de prescription.
Réponds uniquement en JSON :
{{"items": [{{"name": "...", "food_id": null, "ciqual": null, "grams": 0, \
"protein_g": 0, "carbs_g": 0, \
"sugars_g": 0, "fat_g": 0, "sat_fat_g": 0, "fiber_g": 0, \
"sodium_mg": 0}}], "score": 0, "verdict": "...", \
"positives": ["..."], "watch": ["..."]}}"""


def look(description: str, photos: int = 1) -> str:
    """The vision prompt: foods and portions; labels when several photos."""
    return _LOOK.format(
        description=description or "(rien)",
        photos="la photo" if photos <= 1 else f"{photos} photos",
        labels=_LABELS if photos > 1 else "",
    )


def nutrition(context: dict[str, Any]) -> str:
    """The text-model prompt: nutrients per food and assessment."""
    seen = context.get("seen") or []
    return _NUTRITION.format(
        meal=context["meal"],
        time=context["time"],
        description=context.get("description") or "(aucune)",
        seen=json.dumps(seen, ensure_ascii=False) if seen else "(pas de photo)",
        foods=_foods(context.get("foods") or [], context.get("labels") or []),
        refs=_refs(context.get("refs") or []),
        conditions=", ".join(context.get("conditions") or []) or "aucune",
    )


def _foods(foods: list[dict[str, Any]], labels: list[dict[str, Any]]) -> str:
    """The label values the model must use (catalogue, photographed)."""
    if not foods and not labels:
        return ""
    lines = [
        "Étiquettes des produits (valeurs du fabricant pour 100 g, elles "
        "font foi) :"
    ]
    for food in foods:
        lines.append("- " + json.dumps(food, ensure_ascii=False))
    for label in labels:
        lines.append(
            "- photographiée : " + json.dumps(label, ensure_ascii=False)
        )
    return "\n".join(lines) + "\n"


def _refs(refs: list[dict[str, str]]) -> str:
    """The Ciqual references the model picks from (code : name)."""
    if not refs:
        return ""
    lines = ["Références Ciqual (ANSES) possibles, code : nom :"]
    lines += [f"- {r['code']} : {r['name']}" for r in refs]
    return "\n".join(lines) + "\n"
