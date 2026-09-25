"""What comes into and out of the kitchen besides meals: a food's stock.

Only purchases, losses and counts are stored. What was eaten is read
from the meals themselves (their analysed lines of « Mes aliments »), so
a meal changed, read again or deleted changes the stock with it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class StockMove(UUIDMixin, TimestampMixin, Base):
    """One entry of a food's stock: bought, thrown or counted."""

    __tablename__ = "food_stock_moves"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    food_id: Mapped[str] = mapped_column(
        ForeignKey("foods.id", ondelete="CASCADE")
    )
    #: When it was bought, thrown or counted.
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    #: purchase (+), out (thrown, given: −) or count (what is left).
    kind: Mapped[str] = mapped_column(String(12), default="purchase")
    grams: Mapped[float] = mapped_column(Float)
    #: As the user said it: « 3 boîtes », « 6 tomates », « 500 g ».
    said: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    #: web, mcp or raccourci (an iPhone Shortcut's token).
    source: Mapped[str] = mapped_column(String(20), default="web")

    __table_args__ = (Index("ix_food_stock_user_food", "user_id", "food_id"),)
