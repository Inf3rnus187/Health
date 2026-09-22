"""Facts from measured values: markers, exam results, weight."""

from __future__ import annotations

from typing import Any

from app.services.fact_format import Line, day, num


def markers(items: list[dict[str, Any]]) -> list[Line]:
    """Computed markers with their band and freshness."""
    out: list[Line] = []
    for item in items:
        if item["value"] is None:
            continue
        unit = f" {item['unit']}" if item["unit"] else ""
        text = (
            f"{item['label']} : {num(item['value'])}{unit} "
            f"({day(item['date'])}) — {item['interpretation']}"
        )
        if item.get("note"):
            text += f". {item['note']}"
        out.append(("Marqueurs", text))
    return out


def results(items: list[dict[str, Any]]) -> list[Line]:
    """Lab / FibroScan results with the previous value."""
    out: list[Line] = []
    for item in items:
        unit = f" {item['unit']}" if item["unit"] else ""
        latest, prev = item["latest"], item["previous"]
        text = (
            f"{item['label']} : {num(latest['value'])}{unit} "
            f"le {day(latest['date'])}"
        )
        if prev is not None:
            text += (
                f" ; précédent {num(prev['value'])}{unit} le "
                f"{day(prev['date'])} (évolution {num(item['change'])})"
            )
        out.append(("Résultats d'examens", text))
    return out


def weight(found: dict[str, Any] | None) -> list[Line]:
    """Latest weight, changes, trend and loss from the 12-month peak."""
    if not found:
        return []
    latest, peak = found["latest"], found["peak"]
    texts = [
        f"Dernier poids : {num(latest['value'], 1)} kg "
        f"le {day(latest['date'])}"
    ]
    texts += [
        f"Variation sur {c['label']} : {num(c['delta'], 1)} kg "
        f"({num(c['percent'], 1)} %)"
        for c in found["changes"]
        if c["delta"] is not None
    ]
    if found.get("slope_30d") is not None:
        texts.append(f"Tendance : {num(found['slope_30d'], 1)} kg par 30 jours")
    texts.append(
        f"Pic des 12 mois : {num(peak['value'], 1)} kg le "
        f"{day(peak['date'])} ; perte depuis ce pic : "
        f"{num(found['loss_from_peak_pct'], 1)} %"
    )
    return [("Poids", text) for text in texts]
