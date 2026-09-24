"""The foods a user eats often: a box, a sachet — its label, typed once."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, TimestampMixin, UUIDMixin


class Food(UUIDMixin, TimestampMixin, Base):
    """One product: its name, package, per-100 g values and photos.

    Its values come from the manufacturer's label: when a meal names it
    (or the user picks it), they are what the AI reading must use.
    """

    __tablename__ = "foods"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str] = mapped_column(String(120), default="")
    #: Other words naming it in a meal's description (comma-separated).
    aliases: Mapped[str] = mapped_column(Text, default="")
    #: What a box / sachet weighs (g), when it is eaten whole.
    package_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: One unit as the user counts it: « tomate » = 120 g, « tranche »
    #: = 30 g — « 2 tomates » in a meal is then 240 g, every time.
    unit_name: Mapped[str] = mapped_column(String(40), default="")
    unit_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: Where the values come from: « étiquette », « Ciqual 2025 · 20385
    #: Tomate… », « Open Food Facts · 3017620422003 », « saisie ».
    source: Mapped[str] = mapped_column(String(200), default="")
    barcode: Mapped[str] = mapped_column(String(20), default="")
    #: energy_kcal, protein_g, carbs_g, sugars_g, fat_g, sat_fat_g,
    #: fiber_g, sodium_mg — per 100 g, from the label.
    per_100g: Mapped[dict[str, Any]] = mapped_column(JSONColumn, default=dict)
    #: The user's own words (how it is cooked, what is in it…).
    note: Mapped[str] = mapped_column(Text, default="")
    #: [{"id", "kind": "pack" | "label", "path"}] — photos of the pack and
    #: of its nutrition label.
    photos: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONColumn, default=list
    )

    __table_args__ = (Index("ix_foods_user_name", "user_id", "name"),)
