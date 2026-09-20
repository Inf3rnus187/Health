"""Extract lab (biology) results from a text PDF into tracked series.

French lab reports list, per analyte, the current value and one or more
*antériorités* (previous value + its own date). Each becomes a measurement
under a ``bio.<slug>`` metric, so the values flow into the normal trends,
dashboards and reports. Scanned (image-only) PDFs yield no text and are
skipped — those need OCR, handled elsewhere.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from io import BytesIO
from typing import Any, NamedTuple

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec

_LINE = re.compile(
    r"^(?P<name>[A-Za-zÀ-ÿ][^\d]*?)\s+(?:\[AC\]\s+)?"
    r"(?:\d+[.,]\d+\s+%\s+)?(?P<val>\d+(?:[.,]\d+)?)\s+"
    r"(?P<unit>[^\s(]+)\s+\([\d.,]+[-−][\d.,]+\)\s*"
    r"(?P<ant>\d+(?:[.,]\d+)?)?\s*$"
)
_DATE = re.compile(r"^\d{2}[-−]\d{2}[-−]\d{4}$")
_SKIP = {"soit"}


class Reading(NamedTuple):
    """One dated analyte value ready to record."""

    key: str
    label: str
    unit: str
    day: date
    value: float


def parse_text(text: str) -> list[Reading]:
    """Parse a lab report's text into current + antériorité readings."""
    current = _current_date(text)
    ant_date: date | None = None
    out: list[Reading] = []
    for raw in text.splitlines():
        line = raw.strip()
        if _DATE.match(line):
            ant_date = _iso(line)
            continue
        match = _LINE.match(line)
        if match is not None:
            out.extend(_readings(match, current, ant_date))
    return out


async def import_pdf(
    session: AsyncSession, user_id: str, data: bytes
) -> dict[str, Any]:
    """Parse a lab PDF and record its values as measurements."""
    readings = parse_text(_extract(data))
    if not readings:
        return {"added": 0, "metrics": 0, "dates": []}
    cache = MetricCache()
    deduped: dict[tuple[str, date], MeasurementIn] = {}
    for reading in readings:
        spec = MetricSpec(
            reading.key, reading.label, "biology", "float", reading.unit, "last"
        )
        await cache.id_for(session, spec)
        deduped[(reading.key, reading.day)] = MeasurementIn(
            metric_key=reading.key, date_key=reading.day, value=reading.value
        )
    items = list(deduped.values())
    await measure.record_batch(session, user_id, items, source="biology")
    return _summary(readings, len(items))


def _readings(
    match: re.Match[str], current: date, ant_date: date | None
) -> list[Reading]:
    """Build the current and antériorité readings from one line."""
    name = match.group("name").strip()
    slug = _slug(name)
    if not slug or slug in _SKIP:
        return []
    key, unit, label = f"bio.{slug}", match.group("unit"), name[:200]
    out: list[Reading] = []
    value = _to_float(match.group("val"))
    if value is not None:
        out.append(Reading(key, label, unit, current, value))
    ant = _to_float(match.group("ant"))
    if ant is not None and ant_date is not None:
        out.append(Reading(key, label, unit, ant_date, ant))
    return out


def _summary(readings: list[Reading], added: int) -> dict[str, Any]:
    """Build the import summary payload."""
    return {
        "added": added,
        "metrics": len({r.key for r in readings}),
        "dates": sorted({r.day.isoformat() for r in readings}),
    }


def _extract(data: bytes) -> str:
    """Return the concatenated text of every page (empty if scanned)."""
    reader = PdfReader(BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _current_date(text: str) -> date:
    """Find the sample date (prélevé/édité), else today."""
    for label in ("[Pp]r[eé]lev[eé]", "[Ee]dit[eé]"):
        match = re.search(
            rf"{label}\s+le\s+(\d{{2}}[-−]\d{{2}}[-−]\d{{4}})", text
        )
        found = _iso(match.group(1)) if match else None
        if found is not None:
            return found
    return date.today()


def _iso(value: str) -> date | None:
    """Parse a ``DD-MM-YYYY`` (or ``−``) token into a date."""
    match = re.search(r"(\d{2})[-−](\d{2})[-−](\d{4})", value)
    if match is None:
        return None
    return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))


def _slug(name: str) -> str:
    """Accent-stripped snake_case key suffix for an analyte name."""
    norm = unicodedata.normalize("NFKD", name)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", ascii_only).strip("_")


def _to_float(value: str | None) -> float | None:
    """Parse a French-decimal number, or ``None``."""
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None
