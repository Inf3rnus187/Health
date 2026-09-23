"""Find a table's columns by their title, whatever the app's language.

Titles are compared folded (lower case, no accents); the word lists run
from the most to the least specific. A time column must also hold a
date-time in its first filled cell (an "Adresse d'arrivée" column is not
a time).
"""

from __future__ import annotations

import re
from typing import NamedTuple

from app.services import work_parse
from app.services.table_read import Row

START = ("begin trip time", "heure de debut", "request time", "order time",
         "order_time", "date de commande", "date et heure", "date/heure",
         "horodatage", "timestamp", "validation", "entree", "arrivee",
         "check-in", "check in", "checkin", "debut", "start")  # fmt: skip
END = ("dropoff time", "drop-off time", "drop off time", "heure de fin",
       "sortie", "check-out", "check out", "checkout", "end time", "fin",
       "depart", "end")  # fmt: skip
DATE = ("date", "jour", "day")
TIME = ("heure", "time", "hour")
AMOUNT = ("fare amount", "order price", "total ttc", "montant ttc",
          "montant", "total", "prix", "price", "amount", "cout", "cost",
          "ttc", "tarif")  # fmt: skip
CURRENCY = ("currency", "devise", "monnaie")
PLACE = ("begin trip address", "pickup address", "adresse de depart",
         "lieu", "adresse", "address", "station", "gare", "ville",
         "city")  # fmt: skip
VENDOR = ("restaurant", "store", "merchant", "commercant", "etablissement",
          "enseigne", "societe", "fournisseur", "prestataire", "vendor",
          "hotel", "parking")  # fmt: skip
WHAT = ("item name", "item_name", "items", "article", "designation",
        "description", "libelle", "produit", "product", "motif", "objet",
        "nature")  # fmt: skip
STATUS = ("status", "statut", "etat", "state")
ORDER = ("order id", "order_id", "order uuid", "order number",
         "numero de commande", "n° de commande", "id commande")  # fmt: skip
#: Words of a line that say which kind of trace it is (checked in order).
KIND_WORDS = (
    (("uber eats", "deliveroo", "just eat", "livraison"), "livraison"),
    (("taxi", "vtc", "uber", "g7", "bolt", "heetch", "course"), "taxi"),
    (("parking", "stationnement", "indigo", "onepark", "zenpark"), "parking"),
    (("hotel", "nuitee", "ibis", "airbnb", "booking"), "hotel"),
    (("diner", "dejeuner", "petit-dejeuner", "repas", "restaurant",
      "boulangerie", "sandwich"), "repas"),
    (("train", "sncf", "metro", "navigo", "rer", "bus", "tram",
      "transport", "peage"), "transport"),
)  # fmt: skip
#: A row whose status holds one of these words was not carried out.
CANCELLED = re.compile(r"cancel|annul|fail|echou|refus|unfulfil")


class Columns(NamedTuple):
    """The column title for each field (None when absent)."""

    start: str | None
    end: str | None
    date: str | None
    time: str | None
    amount: str | None
    currency: str | None
    place: str | None
    what: str | None
    status: str | None
    order: str | None
    vendor: str | None = None
    kind: str | None = None
    #: Other text columns (a reason, a comment): kept in the description.
    extras: tuple[str, ...] = ()


def find(rows: list[Row]) -> Columns:
    """The columns of a table, from its titles and first values."""
    titles = list(rows[0]) if rows else []
    timed = [t for t in titles if work_parse.stamps(_value(rows, t))]
    dated = [t for t in titles if work_parse.day_of(_value(rows, t))]
    found = Columns(
        start=_pick(timed, START),
        end=_pick(timed, END),
        date=_pick(dated, DATE) or _pick(titles, DATE),
        time=_pick(titles, TIME),
        amount=_pick(titles, AMOUNT),
        currency=_pick(titles, CURRENCY),
        place=_pick(titles, PLACE),
        what=_pick(titles, WHAT),
        status=_pick(titles, STATUS),
        order=_pick(titles, ORDER),
        vendor=_pick(titles, VENDOR),
        kind=_kind_column(rows, titles),
    )
    used = {v for v in found._asdict().values() if isinstance(v, str)}
    rest = [t for t in titles if t not in used and _texty(rows, t)]
    return found._replace(extras=tuple(rest))


def kind_of(text: str) -> str | None:
    """The trace kind a text speaks of (None when it says nothing)."""
    plain = work_parse.fold(text)
    return next(
        (kind for words, kind in KIND_WORDS if any(w in plain for w in words)),
        None,
    )


def amount(text: str) -> float | None:
    """A price in any writing: "18,50 €", "€18.50", "1 234,56"."""
    found = re.search(r"-?\d[\d\s .,]*", text or "")
    if not found:
        return None
    raw = re.sub(r"[\s ]", "", found.group()).rstrip(".,")
    if "," in raw and "." in raw:
        raw = raw.replace("." if raw.rfind(",") > raw.rfind(".") else ",", "")
    try:
        return round(float(raw.replace(",", ".")), 2)
    except ValueError:
        return None


def _pick(titles: list[str], words: tuple[str, ...]) -> str | None:
    """The first title holding the most specific word."""
    folded = {t: work_parse.fold(t) for t in titles}
    for word in words:
        for title, plain in folded.items():
            if word in plain:
                return title
    return None


def _value(rows: list[Row], title: str) -> str:
    """The first filled value of a column."""
    return next((r.get(title, "") for r in rows if r.get(title)), "")


def _kind_column(rows: list[Row], titles: list[str]) -> str | None:
    """The column whose values name a kind (taxi, parking, dîner…)."""
    best, share = None, 0.5
    for title in titles:
        values = [r.get(title, "") for r in rows if r.get(title)]
        if not values:
            continue
        hits = sum(1 for v in values if kind_of(v)) / len(values)
        if hits > share:
            best, share = title, hits
    return best


def _texty(rows: list[Row], title: str) -> bool:
    """Whether a column holds words (not only numbers or dates)."""
    value = _value(rows, title)
    return bool(re.search(r"[a-zA-Z]{3,}", value))
