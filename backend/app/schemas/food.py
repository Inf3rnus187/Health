"""Foods of the catalogue: label values per 100 g, package, photos."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MOST = 60


class Per100g(BaseModel):
    """What 100 g contain, from the manufacturer's label."""

    energy_kcal: float | None = Field(default=None, ge=0, le=900)
    protein_g: float | None = Field(default=None, ge=0, le=100)
    carbs_g: float | None = Field(default=None, ge=0, le=100)
    sugars_g: float | None = Field(default=None, ge=0, le=100)
    fat_g: float | None = Field(default=None, ge=0, le=100)
    sat_fat_g: float | None = Field(default=None, ge=0, le=100)
    fiber_g: float | None = Field(default=None, ge=0, le=100)
    sodium_mg: float | None = Field(default=None, ge=0, le=40000)


class ProductInfo(BaseModel):
    """What Open Food Facts says beyond the 8 values (see food_off_info).

    ``other_100g``: other nutrients in grams per 100 g; ``levels``: fat,
    saturated-fat, sugars, salt → low, moderate or high; ``nova``: 1
    (unprocessed) … 4 (ultra-processed).
    """

    ingredients: str = Field(default="", max_length=4000)
    allergens: list[str] = Field(default_factory=list, max_length=60)
    traces: list[str] = Field(default_factory=list, max_length=60)
    additives: list[str] = Field(default_factory=list, max_length=60)
    nutriscore: str = Field(default="", pattern="^[a-e]?$")
    nutriscore_score: int | None = Field(default=None, ge=-20, le=60)
    nova: int | None = Field(default=None, ge=1, le=4)
    fruits_veg_pct: float | None = Field(default=None, ge=0, le=100)
    levels: dict[str, str] = Field(default_factory=dict)
    labels: str = Field(default="", max_length=500)
    categories: str = Field(default="", max_length=500)
    serving: str = Field(default="", max_length=80)
    other_100g: dict[str, float] = Field(default_factory=dict)
    url: str = Field(default="", max_length=300)

    @field_validator("levels", "other_100g")
    @classmethod
    def _bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        """At most 60 entries with short names."""
        if len(value) > _MOST or any(len(k) > _MOST for k in value):
            raise ValueError("too many or too long entries")
        return value


class FoodIn(BaseModel):
    """Create or change a food (its photos go through their own route)."""

    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(default="", max_length=120)
    aliases: str = Field(default="", max_length=1000)
    package_g: float | None = Field(default=None, gt=0, le=10000)
    #: « 2 tomates » = 2 × unit_g ; unit_name is how it is counted.
    unit_name: str = Field(default="", max_length=40)
    unit_g: float | None = Field(default=None, gt=0, le=5000)
    #: What is usually eaten of it (g): the box, ½, ¼ of the big one.
    portion_g: float | None = Field(default=None, gt=0, le=5000)
    per_100g: Per100g = Field(default_factory=Per100g)
    note: str = Field(default="", max_length=4000)
    source: str = Field(default="", max_length=200)
    barcode: str = Field(default="", max_length=20, pattern=r"^\d{0,20}$")
    #: Open Food Facts' details (ingredients, Nutri-Score, NOVA…); send
    #: them back unchanged when editing, or they are cleared.
    product_info: ProductInfo | None = None


class FoodOut(BaseModel):
    """A food with the ids and kinds of its photos."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    brand: str
    aliases: str
    package_g: float | None
    unit_name: str = ""
    unit_g: float | None = None
    portion_g: float | None = None
    per_100g: dict[str, Any]
    note: str
    source: str = ""
    barcode: str = ""
    product_info: dict[str, Any] | None = None
    photos: list[dict[str, Any]]
    created_at: datetime

    @classmethod
    def of(cls, food: Any) -> FoodOut:
        """The food without its photos' file paths."""
        out = cls.model_validate(food)
        out.photos = [
            {"id": p.get("id"), "kind": p.get("kind")} for p in food.photos
        ]
        return out


class FoodPortion(BaseModel):
    """A catalogue food in a meal, and how much of it (None: estimate)."""

    food_id: str = Field(min_length=1, max_length=36)
    grams: float | None = Field(default=None, gt=0, le=5000)
