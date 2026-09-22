"""Longitudinal photo method v2: anchored rubrics and blinded prompts.

A single daily photo is too noisy to judge (water, meals, bloating,
posture), and a free-text "has it changed?" answer is not measurable.
Each angle is therefore rated on fixed criteria with an *anchored*
0-10 scale (the same written anchors every day, so scores are comparable
over months), plus paired comparisons whose prompt never tells the model
which photo is older (blinded, see :mod:`photo_compare`). Higher scores
always mean more visible abdominal fat. Long lines are data, not logic.
"""

from __future__ import annotations

import math
from typing import Any, NamedTuple

#: Stored as ``PhotoAnalysis.prompt_version``; only this version's
#: analyses feed the long-term statistics.
METHOD = "v2"


class Criterion(NamedTuple):
    """One rated criterion: key, French label, short name, 0-10 anchors."""

    key: str
    label: str
    short: str
    anchors: str


class Horizon(NamedTuple):
    """A comparison horizon: reference photo ~``days`` ago (± tolerance)."""

    key: str
    label: str
    days: int
    tolerance: int


CRITERIA: dict[str, tuple[Criterion, ...]] = {
    "face": (
        Criterion(
            "waist_width",
            "Largeur de taille (face)",
            "waist width relative to the hips and chest",
            "0 = clearly narrow waist with a visible inward curve; 3 = slight waist curve; 5 = straight sides, waist as wide as the hips; 7 = waist wider than the hips, sides bulge outward; 10 = very round apple-shaped trunk, waist much wider than hips and chest",
        ),
        Criterion(
            "abdomen_volume",
            "Volume abdominal (face)",
            "belly volume seen from the front",
            "0 = flat abdomen; 3 = small soft belly below the navel; 5 = rounded belly over the whole abdomen; 7 = large rounded belly with a fold at the navel; 10 = very large belly with deep folds overhanging the pubis",
        ),
    ),
    "profil": (
        Criterion(
            "abdominal_protrusion",
            "Saillie du ventre (profil)",
            "how far the belly sticks out forward",
            "0 = belly flat or behind the chest line; 3 = slight bulge below the navel; 5 = belly clearly in front of the chest line; 7 = globular belly well beyond the chest; 10 = very protruding belly far beyond the chest",
        ),
        Criterion(
            "belly_ptosis",
            "Ventre tombant sous le nombril (profil)",
            "sagging of the lower belly below the navel",
            "0 = no sagging, firm lower belly; 3 = slight lower-belly roundness; 5 = lower belly hangs a little over the waistband; 7 = clear hanging fold; 10 = large apron fold covering the pubis",
        ),
    ),
    "dos": (
        Criterion(
            "flank_fat",
            "Poignées d'amour / flancs (dos)",
            "fat on the flanks (love handles)",
            "0 = no flank fat, straight lines from ribs to hips; 3 = slight bulge above the hips; 5 = clear love handles above the waistband; 7 = large love handles, flanks wider than the ribcage; 10 = very large flank rolls",
        ),
        Criterion(
            "back_rolls",
            "Bourrelets du dos (dos)",
            "skin and fat rolls on the back",
            "0 = smooth back, no rolls; 3 = one faint fold at the lower back; 5 = visible rolls at the lower or mid back; 7 = several marked rolls; 10 = many deep rolls from the shoulder blades to the waist",
        ),
    ),
}

HORIZONS: tuple[Horizon, ...] = (
    Horizon("7d", "vs ~7 jours", 7, 2),
    Horizon("30d", "vs ~1 mois", 30, 7),
    Horizon("90d", "vs ~3 mois", 90, 15),
)

_VIEW = {"face": "front view", "profil": "side view", "dos": "back view"}


def criteria_for(angle: str) -> tuple[Criterion, ...]:
    """Return the rated criteria for an angle (front view by default)."""
    return CRITERIA.get(angle, CRITERIA["face"])


def absolute_prompt(angle: str) -> str:
    """Prompt rating ONE photo on the anchored 0-10 scales (blinded)."""
    scales = "\n".join(
        f'- "{c.key}" ({c.short}): {c.anchors}' for c in criteria_for(angle)
    )
    keys = ", ".join(f'"{c.key}": int' for c in criteria_for(angle))
    return (
        f"You are a clinical anthropometry assistant. Rate this standardized "
        f"{_VIEW.get(angle, 'front view')} progress photo of an adult, used "
        "to follow abdominal fat over months. Rate ONLY what is visible, "
        "never guess weight or a diagnosis. Anchored integer scales 0-10 "
        f"(interpolate between anchors):\n{scales}\n"
        'Also give "pose_ok" (true if standing straight, trunk visible from '
        'neck to hips, belly relaxed, correct view), "confidence" (0 to 1, '
        'how clearly the trunk is visible) and "remarks" (one short '
        "sentence in French). Answer ONLY with a JSON object: "
        f'{{{keys}, "pose_ok": bool, "confidence": number, '
        '"remarks": string}.'
    )


def paired_prompt(angle: str, *, vertical: bool) -> str:
    """Prompt comparing photo 2 with photo 1 (order never revealed)."""
    layout = "1 on top, 2 below" if vertical else "1 on the left, 2 right"
    items = "\n".join(f'- "{c.key}": {c.short}' for c in criteria_for(angle))
    keys = ", ".join(f'"{c.key}": int' for c in criteria_for(angle))
    return (
        "This image holds two standardized "
        f"{_VIEW.get(angle, 'front view')} photos of the same adult, "
        f"labelled 1 and 2 ({layout}), taken on different days. Ignore "
        "lighting, clothing colour and image quality. For each criterion, "
        "compare the person in photo 2 with photo 1 and answer an integer "
        "from -2 to 2: -2 = clearly less in photo 2, -1 = slightly less, "
        "0 = no visible difference, 1 = slightly more, 2 = clearly more.\n"
        f"{items}\nAnswer ONLY with a JSON object: {{{keys}}}."
    )


def read_scores(
    raw: dict[str, Any], angle: str, *, low: int = 0, high: int = 10
) -> dict[str, int]:
    """Keep the criteria answered as numbers, clamped to ``[low, high]``."""
    out: dict[str, int] = {}
    for criterion in criteria_for(angle):
        value = _number(raw.get(criterion.key))
        if value is not None:
            out[criterion.key] = max(low, min(high, round(value)))
    return out


def _number(value: Any) -> float | None:
    """Return a finite numeric model answer (number or numeric string)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value if isinstance(value, int | float) else str(value))
    except ValueError:
        return None
    return number if math.isfinite(number) else None
