"""Extract lab (biology) results from a text PDF into tracked series.

French lab reports list, per analyte, a current value and often an
*antériorité* (a previous value with its own date). Only analytes in the
curated catalog (:mod:`app.services.biology_catalog`) are recorded, each
under a ``bio.<key>`` metric, so a blood test becomes real tracked curves
without polluting the registry with notes or continuation lines. Scanned
(image-only) PDFs yield no extractable text and are skipped — those need
OCR, handled elsewhere.
"""

from __future__ import annotations

import re
from datetime import date
from io import BytesIO
from typing import Any, NamedTuple, cast

from pypdf import PdfReader
from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.schemas.measurement import MeasurementIn
from app.services import biology_catalog as cat
from app.services import measurements as measure
from app.services import ocr
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec

_DATE = re.compile(r"^\d{2}[-−]\d{2}[-−]\d{4}$")
_NUM = r"\d[\d ]*(?:[.,]\d+)?"


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
    out: list[Reading] = []
    pending: cat.Analyte | None = None
    ant_day: date | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if _DATE.match(line):
            ant_day = _iso(line)
            continue
        pending = _consume(line, current, ant_day, out, pending)
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


async def purge(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Delete this user's biology values and any now-empty bio metrics."""
    metric_ids = list(
        (
            await session.execute(
                select(MetricDefinition.id).where(
                    MetricDefinition.key.like(f"{cat.KEY_PREFIX}%")
                )
            )
        ).scalars()
    )
    if not metric_ids:
        return {"values": 0, "metrics": 0}
    values = await session.execute(
        delete(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id.in_(metric_ids),
        )
    )
    deleted = cast("CursorResult[Any]", values).rowcount or 0
    metrics = await _drop_empty(session, metric_ids)
    return {"values": deleted, "metrics": metrics}


def _consume(
    line: str,
    current: date,
    ant_day: date | None,
    out: list[Reading],
    pending: cat.Analyte | None,
) -> cat.Analyte | None:
    """Record any reading on one line; return the next pending analyte."""
    analyte = cat.match(_name_of(line))
    target = analyte or pending
    if target is None:
        return None
    value, ant = _values(line, target)
    if value is None:
        return analyte or pending
    out.extend(_readings(target, current, ant_day, value, ant))
    return None


def _readings(
    analyte: cat.Analyte,
    current: date,
    ant_day: date | None,
    value: float,
    ant: float | None,
) -> list[Reading]:
    """Build the current and antériorité readings for one analyte."""
    key = cat.metric_key(analyte.key)
    out = [Reading(key, analyte.label, analyte.unit, current, value)]
    if ant is not None and ant_day is not None:
        out.append(Reading(key, analyte.label, analyte.unit, ant_day, ant))
    return out


def _values(
    line: str, analyte: cat.Analyte
) -> tuple[float | None, float | None]:
    """Extract (current, antériorité) values for an analyte from a line."""
    match = re.search(rf"({_NUM})\s*{_find_re(analyte.find)}", line)
    if match is None:
        return None, None
    before = line[: match.start()].rstrip()
    if before and before[-1] in "<>=":
        return None, None
    rest = line[match.end() :]
    tail = rest.rsplit(")", 1)[-1] if ")" in rest else rest
    nums = re.findall(_NUM, tail)
    ant = _to_float(nums[-1]) if nums else None
    return _to_float(match.group(1)), ant


def _find_re(find: str) -> str:
    """Regex for a unit token (dimensionless matches a word boundary)."""
    if not find:
        return r"(?!\w)"
    return re.escape(find).replace("µ", "[µμ]") + r"(?![A-Za-z])"


def _name_of(line: str) -> str:
    """The candidate analyte name: text before the first value digit."""
    match = re.search(r"(?<![A-Za-zÀ-ÿ0-9])\d", line)
    return line[: match.start()] if match else line


def _summary(readings: list[Reading], added: int) -> dict[str, Any]:
    """Build the import summary payload."""
    return {
        "added": added,
        "metrics": len({r.key for r in readings}),
        "dates": sorted({r.day.isoformat() for r in readings}),
    }


async def _drop_empty(session: AsyncSession, metric_ids: list[str]) -> int:
    """Delete bio metric definitions that have no measurements left."""
    used = set(
        (
            await session.execute(
                select(Measurement.metric_id)
                .where(Measurement.metric_id.in_(metric_ids))
                .distinct()
            )
        ).scalars()
    )
    empty = [mid for mid in metric_ids if mid not in used]
    if not empty:
        return 0
    result = await session.execute(
        delete(MetricDefinition).where(MetricDefinition.id.in_(empty))
    )
    return cast("CursorResult[Any]", result).rowcount or 0


def _extract(data: bytes) -> str:
    """Text of every page; OCR the PDF when it has no text layer (scanned)."""
    reader = PdfReader(BytesIO(data))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return text if text.strip() else ocr.ocr_pdf(data)


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


def _to_float(value: str | None) -> float | None:
    """Parse a French-decimal number (with thousands spaces), or None."""
    if value is None:
        return None
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return None
