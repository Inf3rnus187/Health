"""Uber's own exports ("Télécharger mes données"): rides and Eats orders.

Read by their exact columns, not guessed:

- ``rider_lifetime_trips``: one ride a line. The times come from the
  ``*_utc`` columns: the ``*_local`` ones are local times written with
  a false "Z". Kept: pickup and drop-off times (and the request), the
  pickup address and the destination as Uber wrote them, the GPS
  points (pickup, real drop-off), distance in km, duration, the price
  shown at booking (after discounts), the tip apart, a business
  profile. A request cancelled or never served is left out (listed
  with its time and place).
- ``user_orders``: one line per item; an order is its establishment
  and its order time. Kept: the establishment, the order and delivery
  times, the items (quantity, options) and the order's price.
  ``City_Name`` is the Uber account's zone ("Paris" for an order 60 km
  away), not the establishment's town: it is not read. A cancelled
  order is left out.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.table_read import Row
from app.services.trace_columns import amount
from app.services.trace_model import Trace

_RIDES = {"request_timestamp_utc", "begintrip_timestamp_utc", "status"}
_EATS = {"restaurant_name", "request_time_local", "order_price"}
_MILE_KM = 1.609344
_NOT_DONE = {
    "rider_canceled": "course annulée par toi",
    "driver_canceled": "course annulée par le chauffeur",
    "unfulfilled": "aucun chauffeur trouvé",
}
_IGNORED = "City_Name : zone du compte Uber, pas le lieu"
Found = tuple[list[Trace], list[dict[str, Any]], dict[str, Any]]


def read(rows: list[Row], tz: ZoneInfo) -> Found | None:
    """An Uber export's traces, lines left out, what was read (or None)."""
    plain = [
        {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        for row in rows
    ]
    titles = set(plain[0]) if plain else set()
    if titles >= _RIDES:
        return _rides(plain, tz)
    if titles >= _EATS:
        return _orders(plain, tz)
    return None


def _rides(rows: list[Row], tz: ZoneInfo) -> Found:
    """Every ride carried out; the other requests listed apart."""
    found: list[Trace] = []
    skipped: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=2):
        start = _utc(row.get("begintrip_timestamp_utc", ""))
        if row.get("status") != "completed" or start is None:
            skipped.append({"line": number, "reason": _left_out(row, tz)})
        else:
            found.append(_ride(row, start, tz))
    about = {
        "document": f"Uber, {len(found)} courses : heures exactes (UTC), "
        "départ → arrivée, GPS, km, prix payé",
        "ignored": _IGNORED.replace("City_Name", "city_name"),
    }
    return found, skipped, about


def _ride(row: Row, start: datetime, tz: ZoneInfo) -> Trace:
    """One ride: pickup → drop-off, the addresses, the price."""
    end = _utc(row.get("dropoff_timestamp_utc", ""))
    pickup, goal = _ends(row)
    product = row.get("global_product_name") or row.get("product_type_name")
    return Trace(
        start=start,
        end=end if end and end > start else None,
        time_known=True,
        kind="taxi",
        place=pickup[:300],
        vendor=f"Uber {product or 'course'} : {pickup} → {goal}"[:200],
        amount=_fare(row),
        currency=(row.get("currency_code") or "EUR")[:3].upper(),
        what=" · ".join(_ride_facts(row, _zone(row, tz)))[:1000],
        group=row.get("request_timestamp_utc", ""),
    )


def _ends(row: Row) -> tuple[str, str]:
    """The pickup address and the destination, as Uber wrote them."""
    pickup = row.get("begintrip_string") or _point(row, "begintrip")
    goal = row.get("destination_string") or _point(row, "destination")
    return pickup or "départ inconnu", goal or "arrivée inconnue"


def _ride_facts(row: Row, zone: ZoneInfo) -> list[str]:
    """What the ride says: places, times, distance, price, GPS."""
    pickup, goal = _ends(row)
    times = [
        (label, _utc(row.get(f"{key}_timestamp_utc", "")))
        for label, key in (
            ("demandée", "request"),
            ("prise en charge", "begintrip"),
            ("déposé", "dropoff"),
        )
    ]
    said = [f"{label} {at.astimezone(zone):%H:%M}" for label, at in times if at]
    return [
        f"Départ : {pickup}",
        f"Arrivée : {goal}",
        ", ".join(said),
        *_trip(row),
        *_paid(row),
        *(["profil pro"] if row.get("profile_type") == "Business" else []),
        *_gps(row),
    ]


def _trip(row: Row) -> list[str]:
    """Distance (km) and duration."""
    miles = _number(row.get("trip_distance_miles", ""))
    seconds = _number(row.get("trip_duration_seconds", ""))
    parts = []
    if miles:
        parts.append(f"{miles * _MILE_KM:.1f} km".replace(".", ","))
    if seconds:
        parts.append(f"{round(seconds / 60)} min")
    return [" en ".join(parts)] if parts else []


def _fare(row: Row) -> float | None:
    """What the ride cost: the price shown at booking, else the fare."""
    for key in ("client_upfront_fare_local", "original_fare_local"):
        value = _number(row.get(key, ""))
        if value:
            return round(value, 2)
    return None


def _paid(row: Row) -> list[str]:
    """The price, the fare before discounts, the tip (paid apart)."""
    price = _fare(row)
    before = _number(row.get("original_fare_local", ""))
    tip = _number(row.get("tip_amount_local_currency", ""))
    parts = [f"prix {_euros(price)}"] if price else []
    if price and before and abs(before - price) >= 0.01:  # noqa: PLR2004
        parts.append(f"avant remise {_euros(before)}")
    if tip:
        parts.append(f"pourboire {_euros(tip)} en plus")
    return parts


def _gps(row: Row) -> list[str]:
    """The pickup point and the real drop-off point."""
    pickup = _point(row, "begintrip") or _point(row, "request")
    drop = _point(row, "dropoff")
    parts = [
        f"départ {pickup}" if pickup else "",
        f"arrivée {drop}" if drop else "",
    ]
    shown = [p for p in parts if p]
    return [f"GPS {' → '.join(shown)}"] if shown else []


def _left_out(row: Row, tz: ZoneInfo) -> str:
    """Why a request is not a ride, with its time and places."""
    status = row.get("status", "")
    why = _NOT_DONE.get(status, f"statut « {status or 'inconnu'} »")
    at = _utc(row.get("request_timestamp_utc", ""))
    when = f"{at.astimezone(_zone(row, tz)):%d/%m/%Y %H:%M}" if at else "?"
    pickup, goal = _ends(row)
    return f"{why} — demandée le {when} : {pickup} → {goal}"


def _orders(rows: list[Row], tz: ZoneInfo) -> Found:
    """The orders (item lines grouped); a cancelled one left out."""
    groups: dict[tuple[str, str], list[tuple[int, Row]]] = {}
    for number, row in enumerate(rows, start=2):
        key = (
            row.get("restaurant_name", ""),
            row.get("request_time_local", ""),
        )
        groups.setdefault(key, []).append((number, row))
    found: list[Trace] = []
    skipped: list[dict[str, Any]] = []
    for (name, stamp), lines in groups.items():
        start, first = _local(stamp, tz), lines[0][1]
        if start is None or "cancel" in first.get("order_status", ""):
            why = "pas de date" if start is None else "commande annulée"
            skipped.append({"line": lines[0][0], "reason": f"{why} — {name}"})
        else:
            found.append(_order(name, start, [r for _, r in lines], tz))
    about = {
        "document": f"Uber Eats, {len(found)} commandes : établissement, "
        "heures de commande et de livraison, articles, prix",
        "ignored": _IGNORED,
    }
    return found, skipped, about


def _order(name: str, start: datetime, lines: list[Row], tz: ZoneInfo) -> Trace:
    """One order: the establishment, ordered → delivered, items, price."""
    first = lines[0]
    end = _local(first.get("final_delivery_time_local", ""), tz)
    return Trace(
        start=start,
        end=end if end and end > start else None,
        time_known=True,
        kind="livraison",
        place="",
        vendor=name[:200],
        amount=amount(first.get("order_price", "")),
        currency=(first.get("currency") or "EUR")[:3].upper(),
        what=", ".join(_items(lines))[:1000],
        group=f"{name}{start:%Y%m%d%H%M%S}",
    )


def _items(lines: list[Row]) -> list[str]:
    """The items; an item's options (one line each) after its name."""
    items: list[list[str]] = []
    last: tuple[str, ...] = ()
    for row in lines:
        key = tuple(
            row.get(k, "") for k in ("item_name", "item_quantity", "item_price")
        )
        option = row.get("customizations", "")
        if items and key == last and option:
            items[-1].append(option)
        else:
            count = int(_number(row.get("item_quantity", "")) or 1)
            label = row.get("item_name", "") or "article"
            items.append([f"{count}× {label}" if count > 1 else label])
            items[-1] += [option] if option else []
        last = key
    return [
        f"{i[0]} ({', '.join(i[1:])})" if len(i) > 1 else i[0] for i in items
    ]


def _utc(text: str) -> datetime | None:
    """A ``*_utc`` time ("2024-02-04T11:31:15.000Z")."""
    try:
        at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (at if at.tzinfo else at.replace(tzinfo=UTC)).astimezone(UTC)


def _local(text: str, tz: ZoneInfo) -> datetime | None:
    """A ``*_local`` time: the wall clock, its "Z" a mistake, in UTC."""
    try:
        at = datetime.fromisoformat(text.rstrip("Zz"))
    except ValueError:
        return None
    return at.replace(tzinfo=tz).astimezone(UTC)


def _zone(row: Row, tz: ZoneInfo) -> ZoneInfo:
    """The ride's time zone (its ``timezone`` column), else the user's."""
    try:
        return ZoneInfo(row.get("timezone") or str(tz))
    except (ZoneInfoNotFoundError, ValueError):
        return tz


def _point(row: Row, key: str) -> str:
    """A GPS point ("49.24761, 2.46218"), empty when absent."""
    lat, lng = (_number(row.get(f"{key}_{c}", "")) for c in ("lat", "lng"))
    return f"{lat:.5f}, {lng:.5f}" if lat and lng else ""


def _number(text: str) -> float | None:
    """A number cell (None when empty or not a number)."""
    try:
        return float(text)
    except ValueError:
        return None


def _euros(value: float) -> str:
    """An amount in euros, French style: ``12,19 €``."""
    return f"{value:.2f} €".replace(".", ",")
