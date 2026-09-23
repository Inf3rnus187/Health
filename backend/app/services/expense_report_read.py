"""Read an expense report PDF (Lucca « Note de frais ») line by line.

Two layouts: the archived report (a page per expense — « Dépense #3 »,
its date, nature, supplier, comment and amount, the scanned receipt
beside) and the printed report (one table: N°, date, nature, supplier,
cost centre, amounts, then the comments numbered below). A report gives
days, not times: each line is known by its day only, and becomes one
trace when a ride or a receipt of the same day and amount is met.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any, NamedTuple

from pypdf import PdfReader

from app.services import trace_columns, work_parse

_TITLE = re.compile(r"(?:note de frais|ndf)\s*(?:n°|#|no\.?)\s*(\d+)", re.I)
_MONTH = re.compile(
    r"\b(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|"
    r"octobre|novembre|decembre)\s+(\d{4})\b"
)
#: When the document was made: printed, else declared.
_WHEN = tuple(
    re.compile(
        rf"{label}\s*:?\s*(\d{{2}}/\d{{2}}/\d{{4}})"
        r"(?:\s*(?:a\s*)?(\d{1,2}):(\d{2}))?"
    )
    for label in ("imprime le", "date de declaration", "declaree le")
)
_AMOUNT = re.compile(r"^-?\d[\d\s .]*,\d{2}(?:\s*\S{1,3})?$")
_NOTE = re.compile(r"^\((\d+)\)\s*(.*)$")
_REF = re.compile(r"\((\d+)\)$")
_GAP = 8.0  # points between two words of one table cell


class Line(NamedTuple):
    """One expense of the report."""

    number: str
    day: date
    nature: str
    vendor: str
    amount: float | None
    paid: str  # "49,00 $ USD" when paid in another currency
    comment: str


class Report(NamedTuple):
    """An expense report: its name, when it was made, its lines."""

    label: str
    issued: datetime | None  # local time, naive
    timed: bool  # whether ``issued`` has its time
    lines: list[Line]


def text_of(data: bytes) -> str:
    """A PDF's text layer (no OCR: a report is always a text PDF)."""
    try:
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 - not a readable PDF: not a report
        return ""


def is_report(text: str) -> bool:
    """Whether a document's text is an expense report (not a receipt)."""
    plain = work_parse.fold(text[:3000])
    return bool(_TITLE.search(plain)) and (
        "depense #" in plain or "declarant" in plain
    )


def read(data: bytes, text: str) -> Report:
    """The report's lines (archived layout, else the printed table)."""
    plain = work_parse.fold(text)
    number = _TITLE.search(plain)
    month = _MONTH.search(plain)
    label = "Note de frais" + (f" n°{number.group(1)}" if number else "")
    if month:
        label += f" — {month.group(1).capitalize()} {month.group(2)}"
    lines = _archived(text) if "Dépense #" in text else _printed(data, text)
    issued, timed = _issued(plain)
    return Report(label=label, issued=issued, timed=timed, lines=lines)


def _issued(plain: str) -> tuple[datetime | None, bool]:
    """When the report was printed, else declared; and if its time is known."""
    found = next((m for p in _WHEN if (m := p.search(plain))), None)
    day = work_parse.day_of(found.group(1)) if found else None
    if found is None or day is None:
        return None, False
    hour, minute = int(found.group(2) or 12), int(found.group(3) or 0)
    at = datetime(day.year, day.month, day.day, hour, minute)
    return at, found.group(2) is not None


def _archived(text: str) -> list[Line]:
    """One line per « Dépense #n » page."""
    out = []
    for chunk in text.split("Dépense #")[1:]:
        rows = [r.strip() for r in chunk.splitlines() if r.strip()]
        day = work_parse.day_of(_after(rows, "Date de la dépense"))
        if day is None or len(rows) < 2:  # noqa: PLR2004
            continue
        spent = next((r for r in rows if r.startswith("Dépensé")), "")
        out.append(
            Line(
                number=rows[0].split()[0],
                day=day,
                nature=rows[1],
                vendor=_between(rows, "Fournisseur", "Source"),
                amount=trace_columns.amount(spent.removeprefix("Dépensé")),
                paid="",
                comment=_between(rows, "Commentaires", "Fournisseur"),
            )
        )
    return out


def _after(rows: list[str], label: str) -> str:
    """The row after a label."""
    at = rows.index(label) if label in rows else -1
    return rows[at + 1] if 0 <= at < len(rows) - 1 else ""


def _between(rows: list[str], first: str, last: str) -> str:
    """The rows between two labels, joined."""
    if first not in rows:
        return ""
    start = rows.index(first) + 1
    end = rows.index(last, start) if last in rows[start:] else start
    return " ".join(rows[start:end])[:300]


def _printed(data: bytes, text: str) -> list[Line]:
    """The printed table: cells found by the gaps between words."""
    notes = _notes(text)
    out = []
    for cells in _cells(data):
        line = _table_line(cells, notes)
        if line is not None:
            out.append(line)
    return out


def _notes(text: str) -> dict[str, str]:
    """The numbered comments under the table: ``{"3": "…"}``."""
    notes: dict[str, str] = {}
    last = ""
    tail = text.split("Commentaires", 1)[-1] if "Commentaires" in text else ""
    for row in tail.splitlines()[1:]:
        found = _NOTE.match(row.strip())
        if found:
            last = found.group(1)
            notes[last] = found.group(2).strip()
        elif last and row.strip():
            notes[last] = f"{notes[last]} {row.strip()}"
    return notes


def _cells(data: bytes) -> list[list[str]]:
    """Each text line of the PDF as its cells (words close together)."""
    import pymupdf

    rows: dict[tuple[int, int], list[Any]] = {}
    doc: Any = pymupdf.open(stream=data, filetype="pdf")  # type: ignore[no-untyped-call]
    for number, page in enumerate(doc):
        for word in page.get_text("words"):
            rows.setdefault((number, round(word[1])), []).append(word)
    out = []
    for key in sorted(rows):
        cells: list[list[str]] = []
        right = -1e9
        for x0, _y0, x1, _y1, word, *_ in sorted(rows[key]):
            if x0 - right > _GAP or not cells:
                cells.append([])
            cells[-1].append(word)
            right = x1
        out.append([" ".join(c) for c in cells])
    return out


def _table_line(cells: list[str], notes: dict[str, str]) -> Line | None:
    """A table row: N°, date, nature, supplier, centre, amounts, (note)."""
    if len(cells) < 4 or not cells[0].isdigit():  # noqa: PLR2004
        return None
    day = work_parse.day_of(cells[1])
    sums = [i for i, c in enumerate(cells) if _AMOUNT.match(c)]
    if day is None or not sums:
        return None
    texts = cells[2 : sums[0]]
    ref = _REF.search(cells[-1])
    paid = cells[sums[0]]
    return Line(
        number=cells[0],
        day=day,
        nature=texts[0] if texts else "",
        vendor=" ".join(texts[1:-1] if len(texts) > 2 else texts[1:]),  # noqa: PLR2004
        amount=trace_columns.amount(cells[sums[-1]]),
        paid="" if "€" in paid or "EUR" in paid else paid,
        comment=notes.get(ref.group(1), "") if ref else "",
    )
