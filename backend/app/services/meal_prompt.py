"""Prompts of the meal reading.

Photo → foods (``look``); foods → grams and references (``nutrition``);
then, once the code has computed every value, the judgement from those
exact values (``assessment``): the model never does the arithmetic the
user reads.
"""

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

_NUTRITION = """Tu es diététicien. Liste les aliments de ce repas.
Repas : {meal} de {time}.
Description du patient (fait foi) : « {description} »
Aliments repérés sur la photo : {seen}
{foods}{refs}Maladies déclarées du patient : {conditions}

Pour chaque aliment, estime la quantité (g) — une quantité donnée \
ci-dessus pour un produit fait foi — puis ses nutriments ramenés à \
cette quantité. Pour un produit dont l'étiquette est donnée ci-dessus, \
utilise ses valeurs (elles font foi : n'écris pas qu'il faudrait \
vérifier sa composition ni son étiquette) et rends son "food_id" ; ses \
informations Open Food Facts (Nutri-Score, groupe NOVA 1 à 4, additifs, \
allergènes, ingrédients, part de fruits et légumes, repères sel et \
sucres) font foi aussi. Pour les autres, \
choisis dans la liste Ciqual la référence la plus proche (même aliment, \
même cuisson ou préparation) et rends son code dans "ciqual" (null si \
aucune ne convient) : ses valeurs seront celles de la table. \
Respecte la description : si elle dit sans huile, beurre, sauce ou \
graisse, n'en ajoute pas. N'invente aucun aliment absent de la \
description et de la photo.
Réponds uniquement en JSON :
{{"items": [{{"name": "...", "food_id": null, "ciqual": null, "grams": 0, \
"protein_g": 0, "carbs_g": 0, \
"sugars_g": 0, "fat_g": 0, "sat_fat_g": 0, "fiber_g": 0, \
"sodium_mg": 0}}]}}"""

_ASSESS = """Tu es diététicien et médecin nutritionniste. Juge ce repas \
pour CE patient.
Repas : {meal} de {time}.
Description du patient (fait foi) : « {description} »
Aliments repérés sur la photo : {seen}
Maladies déclarées du patient : {conditions}
Ce qu'il a mangé, calculé par le logiciel (ses fiches d'aliments, \
leurs étiquettes et Open Food Facts, la table Ciqual) — quantités et \
nutriments EXACTS :
{items}
Total du repas : {totals}
{products}
Donne une note de 0 (à éviter) à 10 (idéal), un verdict en une phrase, \
les points positifs, les points à surveiller. Les chiffres ci-dessus \
sont exacts : ne les recalcule jamais ; pour citer une quantité ou un \
nutriment, recopie exactement le chiffre donné, avec son unité. \
N'écris pas qu'il faudrait vérifier une étiquette ou une composition. \
Pas de posologie ni de prescription.
Réponds uniquement en JSON :
{{"score": 0, "verdict": "...", "positives": ["..."], "watch": ["..."]}}"""
_NAMES = (
    ("energy_kcal", "énergie", "kcal"),
    ("protein_g", "protéines", "g"),
    ("carbs_g", "glucides", "g"),
    ("sugars_g", "dont sucres", "g"),
    ("fat_g", "lipides", "g"),
    ("sat_fat_g", "dont saturés", "g"),
    ("fiber_g", "fibres", "g"),
    ("sodium_mg", "sodium", "mg"),
)
_FROM = {
    "écrit": "écrits par le patient",
    "compté": "comptés avec l'unité de sa fiche",
    "portion": "sa portion habituelle",
    "formulaire": "saisis par le patient",
    "paquet": "le paquet entier",
    "IA": "estimés",
    "défaut": "estimés",
}


def look(description: str, photos: int = 1) -> str:
    """The vision prompt: foods and portions; labels when several photos."""
    return _LOOK.format(
        description=description or "(rien)",
        photos="la photo" if photos <= 1 else f"{photos} photos",
        labels=_LABELS if photos > 1 else "",
    )


def nutrition(context: dict[str, Any]) -> str:
    """The text-model prompt: each food, its grams and its reference."""
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


def assessment(
    context: dict[str, Any],
    items: list[dict[str, Any]],
    totals: dict[str, float],
) -> str:
    """The judgement prompt: the code's exact values, the product details."""
    seen = context.get("seen") or []
    return _ASSESS.format(
        meal=context["meal"],
        time=context["time"],
        description=context.get("description") or "(aucune)",
        seen=json.dumps(seen, ensure_ascii=False) if seen else "(pas de photo)",
        conditions=", ".join(context.get("conditions") or []) or "aucune",
        items="\n".join(f"- {_line(item)}" for item in items) or "(rien)",
        totals=_values(totals),
        products=_products(context.get("foods") or []),
    )


def _line(item: dict[str, Any]) -> str:
    """« Tomates : 240 g (estimés, Ciqual) — énergie 46,1 kcal, … »."""
    grams = _number(float(item.get("grams") or 0))
    said = _FROM.get(str(item.get("grams_from") or ""), "estimés")
    source = item.get("source") or "estimation"
    return f"{item['name']} : {grams} g ({said}, {source}) — {_values(item)}"


def _values(found: dict[str, Any]) -> str:
    """« énergie 153,6 kcal, protéines 2,2 g, … » (French decimals)."""
    return ", ".join(
        f"{name} {_number(float(found.get(key) or 0))} {unit}"
        for key, name, unit in _NAMES
    )


def _number(value: float) -> str:
    """One decimal at most, with a comma: 562.4 → « 562,4 »."""
    return f"{round(value, 1):g}".replace(".", ",")


def _products(foods: list[dict[str, Any]]) -> str:
    """Open Food Facts' details of the user's foods (authoritative)."""
    found = [f for f in foods if f.get("open_food_facts")]
    if not found:
        return ""
    lines = ["Informations Open Food Facts (font foi) :"]
    lines += [
        f"- {f['name']} : "
        + json.dumps(f["open_food_facts"], ensure_ascii=False)
        for f in found
    ]
    return "\n".join(lines) + "\n"


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
