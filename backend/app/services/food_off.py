"""A packaged food by its barcode, from Open Food Facts (optional).

Off unless ``FOOD_LOOKUP_ONLINE=true``: then the hub asks
``/api/v2/product/<barcode>.json`` — only the barcode is sent, never who
asks or what they ate. Open Food Facts is collaborative (ODbL): its
values are a proposal to check against the pack, like a label read by
the AI; nothing is saved until the user saves the food. Besides the 8
values, every detail the product page gives (ingredients, Nutri-Score,
NOVA, additives, allergens, other nutrients…) comes as
``product_info`` (:mod:`food_off_info`).
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import InvalidInputError, NotFoundError
from app.services import food_label, food_off_info

_BARCODE = re.compile(r"^\d{8,14}$")
_FIELDS = (
    "product_name,product_name_fr,brands,product_quantity,nutriments,"
    + food_off_info.FIELDS
)
#: Our name → Open Food Facts nutriment per 100 g.
_NUTRIMENTS = {
    "energy_kcal": "energy-kcal_100g",
    "protein_g": "proteins_100g",
    "carbs_g": "carbohydrates_100g",
    "sugars_g": "sugars_100g",
    "fat_g": "fat_100g",
    "sat_fat_g": "saturated-fat_100g",
    "fiber_g": "fiber_100g",
    "salt_g": "salt_100g",
}
_SODIUM = "sodium_100g"  # grams: taken as given, not recomputed from salt
_TIMEOUT = 10.0


async def lookup(barcode: str) -> dict[str, Any]:
    """Name, brand, net weight, values per 100 g and every detail."""
    settings = get_settings()
    if not settings.food_lookup_online:
        raise InvalidInputError(
            "Recherche en ligne désactivée (FOOD_LOOKUP_ONLINE=true dans "
            "le .env pour l'activer)"
        )
    if not _BARCODE.match(barcode):
        raise InvalidInputError("Un code-barres a 8 à 14 chiffres")
    product = await _product(settings.openfoodfacts_url, barcode)
    return {
        "name": str(
            product.get("product_name_fr") or product.get("product_name") or ""
        )[:200],
        "brand": str(product.get("brands") or "").split(",")[0].strip()[:120],
        "package_g": food_label.grams(product.get("product_quantity")),
        "per_100g": food_label.values(_per_100g(product.get("nutriments"))),
        "barcode": barcode,
        "source": f"Open Food Facts · {barcode}",
        "product_info": food_off_info.info(product, barcode),
    }


async def _product(base: str, barcode: str) -> dict[str, Any]:
    """The product's fields, or NotFound."""
    url = f"{base.rstrip('/')}/api/v2/product/{barcode}.json"
    headers = {"User-Agent": "PhoenixHealthHub/1.0 (self-hosted)"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as http:
            response = await http.get(url, params={"fields": _FIELDS})
    except httpx.HTTPError as exc:
        raise InvalidInputError("Open Food Facts injoignable") from exc
    body = response.json() if response.is_success else {}
    if not isinstance(body, dict) or body.get("status") != 1:
        raise NotFoundError("Produit inconnu d'Open Food Facts")
    product = body.get("product")
    return product if isinstance(product, dict) else {}


def _per_100g(nutriments: Any) -> dict[str, Any]:
    """Open Food Facts' values per 100 g, under our names."""
    found = nutriments if isinstance(nutriments, dict) else {}
    values = {ours: found.get(theirs) for ours, theirs in _NUTRIMENTS.items()}
    sodium = found.get(_SODIUM)
    if isinstance(sodium, int | float) and not isinstance(sodium, bool):
        values["sodium_mg"] = round(float(sodium) * 1000, 1)
    return values
