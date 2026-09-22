"""Turn a HealthKit category event into a number a day can aggregate.

A symptom becomes its severity (0 absent … 3 severe), a flow 0-3, a
positive test 1, a notification / hand-wash / sexual activity 1 (so the
day sums to a count), a mindfulness session its minutes, a stand hour 1
when stood. Unknown or indeterminate values stay non-numeric.
"""

from __future__ import annotations

from datetime import datetime

from app.services.apple_health import hk_catalog

_P = "HKCategoryValue"
#: Value family → {raw value suffix → number}.
_TABLES: dict[str, dict[str, float]] = {
    "severity": {
        "SeverityNotPresent": 0.0,
        "SeverityUnspecified": 1.0,
        "SeverityMild": 1.0,
        "SeverityModerate": 2.0,
        "SeveritySevere": 3.0,
    },
    "presence": {"PresencePresent": 1.0, "PresenceNotPresent": 0.0},
    "appetite": {
        "AppetiteChangesUnspecified": 1.0,
        "AppetiteChangesNoChange": 0.0,
        "AppetiteChangesDecreased": 1.0,
        "AppetiteChangesIncreased": 1.0,
    },
    "stand": {"AppleStandHourStood": 1.0, "AppleStandHourIdle": 0.0},
    "flow": {
        "None": 0.0,
        "Unspecified": 1.0,
        "Light": 1.0,
        "Medium": 2.0,
        "Heavy": 3.0,
    },
    "mucus": {
        "CervicalMucusQualityDry": 1.0,
        "CervicalMucusQualitySticky": 2.0,
        "CervicalMucusQualityCreamy": 3.0,
        "CervicalMucusQualityWatery": 4.0,
        "CervicalMucusQualityEggWhite": 5.0,
    },
    "test": {
        "Negative": 0.0,
        "Positive": 1.0,
        "LuteinizingHormoneSurge": 1.0,
        "EstrogenSurge": 1.0,
    },
    "menopause": {
        "MenopausalStateNone": 0.0,
        "MenopausalStatePerimenopause": 1.0,
        "MenopausalStateMenopause": 2.0,
    },
}
#: Families whose raw value embeds a type-specific prefix before the key.
_SUFFIX_ONLY = frozenset({"flow", "test"})


def category_value(
    hk_type: str, raw: str | None, start: datetime | None, end: datetime | None
) -> float | None:
    """The number a category event stands for (None when unknown)."""
    spec = hk_catalog.TYPES.get(hk_type)
    if spec is None or not spec.family:
        return None
    if spec.family == "count":
        return 1.0
    if spec.family == "duration":
        return _minutes(start, end)
    return _lookup(spec.family, raw or "")


def _lookup(family: str, raw: str) -> float | None:
    """Look a raw ``HKCategoryValue…`` string up in its family table."""
    table = _TABLES.get(family, {})
    value = raw.removeprefix(_P)
    if family in _SUFFIX_ONLY:
        return next(
            (num for key, num in table.items() if value.endswith(key)), None
        )
    return table.get(value)


def _minutes(start: datetime | None, end: datetime | None) -> float | None:
    """Duration of an interval in minutes."""
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds() / 60.0, 2)
