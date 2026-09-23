"""Work hours as a file: sessions, days, weeks or months (csv/json/xlsx)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import Workbook

LEVELS = ("sessions", "days", "weeks", "months")
_MEDIA = {
    "csv": "text/csv",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def rows(
    stats: dict[str, Any],
    sessions: list[dict[str, Any]],
    level: str,
    tz: ZoneInfo,
) -> list[dict[str, Any]]:
    """The table of one level, with French column names."""
    if level == "sessions":
        return [_session(s, tz) for s in reversed(sessions)]
    build = {"weeks": _week, "months": _month}.get(level, _day)
    return [build(item) for item in stats[level if level in LEVELS else "days"]]


def render(table: list[dict[str, Any]], fmt: str) -> tuple[bytes, str]:
    """The table as bytes and its media type."""
    if fmt == "json":
        text = json.dumps(table, default=str, ensure_ascii=False, indent=1)
        return text.encode(), _MEDIA["json"]
    if fmt == "xlsx":
        return _xlsx(table), _MEDIA["xlsx"]
    out = io.StringIO()
    if table:
        writer = csv.DictWriter(out, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    return out.getvalue().encode("utf-8-sig"), _MEDIA["csv"]


def _day(d: dict[str, Any]) -> dict[str, Any]:
    """One worked day."""
    return {
        "jour": d["date"],
        "embauche": d["start_text"] or "",
        "debauche": d["end_text"] or "",
        "heures": d["hours"],
    }


def _week(w: dict[str, Any]) -> dict[str, Any]:
    """One ISO week with its overtime and the 48 h flag."""
    return {
        "semaine": w["week"],
        "lundi": w["monday"],
        "heures": w["hours"],
        "jours": w["days"],
        "heures_sup": w["overtime"],
        "plus_de_48h": "oui" if w["over_48h"] else "non",
    }


def _month(m: dict[str, Any]) -> dict[str, Any]:
    """One month."""
    return {
        "mois": m["month"],
        "heures": m["hours"],
        "jours": m["days"],
        "heures_sup": m["overtime"],
    }


def _session(row: dict[str, Any], tz: ZoneInfo) -> dict[str, Any]:
    """One session with local times."""
    end = row["end_at"]
    return {
        "jour": row["date_key"],
        "embauche": f"{row['start_at'].astimezone(tz):%H:%M}",
        "debauche": f"{end.astimezone(tz):%H:%M}" if end else "",
        "heures": row["hours"],
        "source": row["source"],
        "note": row["note"],
    }


def _xlsx(table: list[dict[str, Any]]) -> bytes:
    """A one-sheet workbook."""
    book = Workbook()
    sheet = book.active
    if sheet is not None and table:
        sheet.append(list(table[0]))
        for row in table:
            sheet.append(
                [str(v) if v is not None else "" for v in row.values()]
            )
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def _cell(value: Any) -> Any:
    """A spreadsheet cell: numbers stay numbers."""
    if value is None:
        return ""
    return value if isinstance(value, int | float | str) else str(value)
