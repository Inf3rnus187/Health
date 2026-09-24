"""What a clinical report adds to its values: facts and its stamp.

The facts of the period (habits, adherence, meals, traceability, with
the report's ``compare_from`` if asked) and the stamp: when it was made
(local time and zone), the version running, and the SHA-256 of the data
it was built on (values and facts) — printed in the header.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.report import Report
from app.services import report_facts
from app.services.daily_rollup import user_zone


async def gather(
    session: AsyncSession,
    report: Report,
    rows: list[dict[str, Any]],
    span: tuple[date, date],
) -> dict[str, Any]:
    """The facts and the stamp of a clinical report."""
    split = _split((report.params or {}).get("compare_from"))
    facts = await report_facts.gather(session, report.user_id, span, split)
    zone = await user_zone(session, report.user_id)
    made = datetime.now(zone)
    data = json.dumps([rows, facts], sort_keys=True, default=str)
    return {
        "facts": facts,
        "stamp": {
            "generated": f"{made:%d/%m/%Y %H:%M:%S} ({zone.key})",
            "version": get_settings().git_commit,
            "data_sha256": hashlib.sha256(data.encode()).hexdigest(),
        },
    }


def _split(value: Any) -> date | None:
    """The ``compare_from`` day asked, or None."""
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None
