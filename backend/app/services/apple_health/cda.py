"""Extract observations from an Apple ``export_cda.xml`` document.

CDA (HL7 Clinical Document Architecture) holds labs, vitals and other
clinical results as nested ``<observation>`` elements. This streams the
document and yields the ones that carry a value, so they can be stored
and browsed.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import IO, NamedTuple
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import iterparse

_TS_MIN_LEN = 8


class Observation(NamedTuple):
    """One clinical observation with a label, value and date."""

    label: str
    value_num: float | None
    value_text: str | None
    unit: str | None
    effective_at: datetime | None


def iter_observations(source: IO[bytes]) -> Iterator[Observation]:
    """Yield every value-bearing observation in the document."""
    for _event, elem in iterparse(source, events=("end",)):
        if _local(elem.tag) != "observation":
            continue
        obs = _build(elem)
        if obs is not None:
            yield obs
        elem.clear()


def _local(tag: str) -> str:
    """Strip the XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1]


def _child(elem: Element, name: str) -> Element | None:
    """Return the first direct child with the given local name."""
    for child in elem:
        if _local(child.tag) == name:
            return child
    return None


def _build(elem: Element) -> Observation | None:
    """Build an observation, or None when it carries no value/label."""
    label = _label(elem)
    num, text, unit = _value(elem)
    if not label or (num is None and text is None):
        return None
    return Observation(label[:200], num, text, unit, _time(elem))


def _label(elem: Element) -> str:
    """Return the observation's display name or code."""
    code = _child(elem, "code")
    if code is None:
        return ""
    return code.get("displayName") or code.get("code") or ""


def _value(elem: Element) -> tuple[float | None, str | None, str | None]:
    """Return (numeric, text, unit) from the observation's value node."""
    node = _child(elem, "value")
    if node is None:
        return None, None, None
    raw = node.get("value")
    if raw is not None:
        return _numeric(raw, node.get("unit"))
    text = node.get("displayName") or (node.text or "").strip() or None
    return None, text, None


def _numeric(
    raw: str, unit: str | None
) -> tuple[float | None, str | None, str | None]:
    """Coerce a PQ value to a number, falling back to text."""
    try:
        return float(raw), None, unit
    except ValueError:
        return None, raw, unit


def _time(elem: Element) -> datetime | None:
    """Parse the observation's effectiveTime (HL7 ``YYYYMMDD…``)."""
    node = _child(elem, "effectiveTime")
    raw = node.get("value") if node is not None else None
    if not raw or len(raw) < _TS_MIN_LEN:
        return None
    try:
        return datetime.strptime(raw[:8], "%Y%m%d")
    except ValueError:
        return None
