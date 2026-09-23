"""Read a receipt or an invoice (PDF, photo) as one trace.

Ride, delivery, parking, hotel receipts: the day — and the time when the
file name or the text gives it (Uber names its receipts
``09-05-2026-03H47-…``) —, the total paid, who billed it, what for, and
the file itself kept as the proof (SHA-256). A photo or a scanned PDF is
read by OCR.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.services import document_text, trace_columns, work_parse

#: File starts of the documents read here (PDF, PNG, JPEG).
_MAGIC = (b"%PDF-", b"\x89PNG", b"\xff\xd8\xff")
#: Total labels, most specific first (folded).
_TOTALS = ("montant total a payer", "total a payer", "net a payer",
           "total ttc", "montant ttc", "total paye", "montant paye",
           "total", "montant", "amount")  # fmt: skip
_MONEY = re.compile(r"\d[\d\s ]*[.,]\d{2}")
_BRANDS = {"uber eats": "Uber Eats", "uber": "Uber", "g7": "G7",
           "bolt": "Bolt", "heetch": "Heetch", "deliveroo": "Deliveroo",
           "just eat": "Just Eat", "sncf": "SNCF", "indigo": "Indigo",
           "onepark": "Onepark", "zenpark": "Zenpark", "ibis": "ibis",
           "booking": "Booking"}  # fmt: skip
_INVOICE = re.compile(
    r"(?:numero de facture|n[°o] de facture|facture n[°o]?)\s*:?\s*(\S+)"
)
_NOON = time(12, 0)
_SEP, _TSEP = r"[-_. ]", r"[-_. tT]*"
#: File-name date-times: (pattern, meaning of its groups).
_NAMES = (
    (re.compile(rf"(?<!\d)(\d{{1,2}}){_SEP}(\d{{1,2}}){_SEP}(\d{{4}}){_TSEP}"
                r"(\d{1,2})[hH:._-](\d{2})(?!\d)"), "dmyhi"),
    (re.compile(rf"(?<!\d)(\d{{4}}){_SEP}(\d{{1,2}}){_SEP}(\d{{1,2}}){_TSEP}"
                r"(\d{1,2})[hH:._-](\d{2})(?!\d)"), "ymdhi"),
    (re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})[-_tT ](\d{2})(\d{2})(?!\d)"),
     "ymdhi"),
)  # fmt: skip
_MEDIA = {b"%PDF-": "application/pdf", b"\x89PNG": "image/png"}


class Receipt(NamedTuple):
    """What a receipt says (``start`` in the user's time zone)."""

    start: datetime
    time_known: bool
    amount: float | None
    vendor: str
    what: str
    kind: str | None
    media_type: str


def is_receipt(data: bytes, name: str) -> bool:
    """Whether a file is a document to read (not a table)."""
    return data.startswith(_MAGIC) or name.lower().endswith(
        (".pdf", ".png", ".jpg", ".jpeg")
    )


def read(data: bytes, name: str, tz: ZoneInfo) -> Receipt | None:
    """The receipt's trace (None when no date can be found)."""
    media = next(
        (m for magic, m in _MEDIA.items() if data.startswith(magic)),
        "image/jpeg",
    )
    text = document_text.extract(data, media).text
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    folded = [work_parse.fold(line) for line in lines]
    when = _when(name, text, tz)
    if when is None:
        return None
    return Receipt(
        start=when[0],
        time_known=when[1],
        amount=_total(lines, folded),
        vendor=_vendor(lines, folded),
        what=_what(lines, folded),
        kind=trace_columns.kind_of(" ".join(folded[:40])),
        media_type=media,
    )


def name_stamp(name: str) -> datetime | None:
    """The date and time a file is named after (local, naive).

    ``09-05-2026-03H47-…``, ``2026-05-09_03-47``, ``09.05.2026 03.47``,
    ``20260509-0347``: the day first or the year first, any separator.
    """
    for pattern, order in _NAMES:
        found = pattern.search(name)
        if found:
            parts = dict(zip(order, map(int, found.groups()), strict=True))
            try:
                return datetime(
                    parts["y"], parts["m"], parts["d"], parts["h"], parts["i"]
                )
            except ValueError:
                continue
    return None


def _when(name: str, text: str, tz: ZoneInfo) -> tuple[datetime, bool] | None:
    """The time from the file name, else the text; else the day at noon."""
    day = work_parse.day_of(text)
    stamp = name_stamp(name)
    named = [stamp] if stamp else []
    if named and (
        day is None or abs(named[0].date() - day) <= timedelta(days=1)
    ):
        return named[0].replace(tzinfo=tz), True
    stamped = next(
        (s for line in text.splitlines() for s in work_parse.stamps(line)), None
    )
    if stamped is not None and (day is None or stamped.date() == day):
        return (stamped if stamped.tzinfo else stamped.replace(tzinfo=tz)), True
    first: date | None = day or (named[0].date() if named else None)
    if first is None:
        return None
    return datetime.combine(first, _NOON, tzinfo=tz), False


def _total(lines: list[str], folded: list[str]) -> float | None:
    """The total paid: after the most specific total label, else the max."""
    for label in _TOTALS:
        for i, line in enumerate(folded):
            if label in line:
                for candidate in lines[i : i + 3]:
                    money = _MONEY.search(candidate)
                    if money:
                        return trace_columns.amount(money.group())
    amounts = [
        trace_columns.amount(m) for m in _MONEY.findall("\n".join(lines))
    ]
    known = [a for a in amounts if a is not None]
    return max(known) if known else None


def _vendor(lines: list[str], folded: list[str]) -> str:
    """The brand, and who billed through it (``… pour:`` next line)."""
    text = " ".join(folded)
    brand = next((label for key, label in _BRANDS.items() if key in text), "")
    billed = next(
        (
            lines[i + 1]
            for i, line in enumerate(folded[:-1])
            if line.endswith("pour:")
        ),
        "",
    )
    return " — ".join(part for part in (brand, billed) if part)[:300]


def _what(lines: list[str], folded: list[str]) -> str:
    """The items billed and the invoice number."""
    start = next(
        (i for i, f in enumerate(folded) if f.startswith("description")), None
    )
    items: list[str] = []
    if start is not None:
        for line, plain in zip(
            lines[start + 1 :], folded[start + 1 :], strict=False
        ):
            if plain.startswith("total"):
                break
            if re.search(r"[a-z]{4,}", plain) and not re.search(
                r"\d|€|qte|tva|montant", plain
            ):
                items.append(line)
    number = _INVOICE.search(" ".join(folded))
    if number:
        items.append(f"facture {number.group(1).upper()}")
    return " ; ".join(items)[:500]
