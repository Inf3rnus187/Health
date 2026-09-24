"""Facts for the AI synthesis: how each treatment was followed (30 days).

One line per treatment with doses recorded: doses planned and taken,
the rate, days without any entry, the longest gap, the usual time, how
many were entered afterwards — the synthesis may then say whether a
treatment is followed, from what was actually recorded.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import medication_stats

Line = tuple[str, str]
_SECTION = "Observance des traitements (30 derniers jours)"


async def adherence(session: AsyncSession, user_id: str) -> list[Line]:
    """The last 30 days' adherence of every treatment with a record."""
    span = await medication_stats.span(session, user_id, None, None)
    found = await medication_stats.adherence(session, user_id, span)
    return [(_SECTION, _text(i)) for i in found["items"] if _recorded(i)]


def _recorded(item: dict[str, Any]) -> bool:
    """Something was entered (a dose taken or declared not taken)."""
    return bool(item["taken"] or item["skipped"])


def _text(item: dict[str, Any]) -> str:
    """« Traitement A : 28 prises notées sur 30 prévues (93 %)… »."""
    planned = item.get("planned")
    rate = item.get("rate")
    head = (
        f"{item['name']} : {item['taken']} prises notées sur {planned} "
        f"prévues ({rate:g} %)"
        if planned
        else f"{item['name']} (à la demande) : {item['taken']} prises notées"
    )
    return (
        f"{head}, {item['skipped']} déclarées non prises, "
        f"{item['days_without_record']} jours sans aucune saisie sur "
        f"{item['days']}, plus long trou {item['longest_gap_days']} jours, "
        f"heure habituelle {item.get('usual_time') or 'inconnue'}, "
        f"{item['entered_late']} saisies plus d'une heure après la prise"
    )
