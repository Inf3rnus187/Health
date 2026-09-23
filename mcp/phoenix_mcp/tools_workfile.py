"""Tools: the work ↔ health file — logs, absences, evidence, nights."""

from __future__ import annotations

import base64
from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def import_logs(files: list[dict[str, str]], dry_run: bool = True) -> Any:
    """Import iPhone Shortcut history files (one time stamp per line).

    ``files``: [{"filename": "Embauche.txt", "text": "...", "key": ""}].
    The key comes from the file name when empty: work.start (Embauche),
    work.end (Débauche), habit.cigarettes, habit.coffee,
    water.bottles_1_5, elimination.urination. Send clock-in and clock-out
    files together so they are paired. First call with dry_run=true, show
    the user what was read, import for real once they agree.
    """
    upload = [
        ("files", (f["filename"], f["text"].encode(), "text/plain"))
        for f in files
    ]
    data = {"keys": [f.get("key", "") for f in files]}
    flag = "true" if dry_run else "false"
    return await client.upload(f"/logs/import?dry_run={flag}", upload, data)


@mcp.tool()
async def list_absences(
    start: str | None = None, end: str | None = None
) -> Any:
    """Absences (sick leave, work accident…) with their cause."""
    return await client.get("/absences", {"start": start, "end": end})


@mcp.tool()
async def save_absence(
    start_date: str,
    end_date: str,
    kind: str = "arret_maladie",
    cause: str = "",
    note: str = "",
    absence_id: str | None = None,
) -> Any:
    """Record (or replace, with ``absence_id``) an absence.

    kind: arret_maladie, accident_travail, maladie_pro, conge or autre.
    """
    body = {"start_date": start_date, "end_date": end_date, "kind": kind,
            "cause": cause, "note": note}  # fmt: skip
    if absence_id:
        return await client.request("PUT", f"/absences/{absence_id}", body=body)
    return await client.post("/absences", body)


@mcp.tool()
async def delete_absence(absence_id: str) -> Any:
    """Delete an absence (ask the user first)."""
    return await client.request("DELETE", f"/absences/{absence_id}")


@mcp.tool()
async def list_evidence(
    start: str | None = None, end: str | None = None
) -> Any:
    """Evidence (calls, mails, screenshots…) with their SHA-256."""
    return await client.get("/evidence", {"start": start, "end": end})


@mcp.tool()
async def add_evidence(
    occurred_at: str,
    kind: str = "capture",
    title: str = "",
    description: str = "",
    count: int = 1,
    trace: dict[str, Any] | None = None,
    file: dict[str, str] | None = None,
) -> Any:
    """Add a proof or a trace: when, kind, how many, what it shows.

    Proofs: appel, sms, mail, capture, note, document, autre. Traces
    (a third party saw you): transport, taxi, parking, livraison, repas,
    hotel, frais. ``trace``: {"ended_at", "place", "amount", "currency",
    "meal": true} — "meal" logs a delivery / meal bought as a meal with
    its price (AI-read). ``file``: {"base64", "filename", "media_type"}.
    """
    data = {"occurred_at": occurred_at, "kind": kind, "title": title,
            "description": description, "count": str(count)}  # fmt: skip
    for key, value in (trace or {}).items():
        if value is not None:
            data[key] = (
                str(value).lower() if isinstance(value, bool) else str(value)
            )
    files: list[Any] = []
    if file and file.get("base64"):
        raw = base64.b64decode(file["base64"])
        name = file.get("filename", "preuve.png")
        files.append(("file", (name, raw, file.get("media_type", "image/png"))))
    return await client.upload("/evidence", files, data)


@mcp.tool()
async def import_traces(
    files: list[dict[str, str]], meals: bool = True, dry_run: bool = True
) -> Any:
    """Import app exports as traces (Uber, Uber Eats, Navigo, parking).

    ``files``: [{"filename": "trips_data.csv", "text": "...", "kind":
    "taxi"}] — kind: transport, taxi, parking, livraison, repas, hotel or
    frais; CSV or JSON text (columns found by their titles). ``meals``
    logs each delivery as a meal with its price. Dry run first, then
    import for real once the user agrees.
    """
    upload = [
        ("files", (f["filename"], f["text"].encode(), "text/plain"))
        for f in files
    ]
    data = {"kinds": [f["kind"] for f in files]}
    flags = f"dry_run={str(dry_run).lower()}&meals={str(meals).lower()}"
    return await client.upload(f"/traces/import?{flags}", upload, data)


@mcp.tool()
async def delete_evidence(item_id: str) -> Any:
    """Delete one evidence item and its file (ask the user first)."""
    return await client.request("DELETE", f"/evidence/{item_id}")


@mcp.tool()
async def sleep_nights(start: str | None = None, end: str | None = None) -> Any:
    """Nights by wake-up day: asleep, awakenings, blocks, bed / wake times.

    Days without any sleep data are listed as missing (watch not worn).
    """
    return await client.get("/sleep/nights", {"start": start, "end": end})


@mcp.tool()
async def add_sleep_night(
    bedtime: str, wake_time: str, awakenings: int | None = None
) -> Any:
    """Type a night the watch missed (ISO local times; confirm first)."""
    body = {"bedtime": bedtime, "wake_time": wake_time,
            "awakenings": awakenings}  # fmt: skip
    return await client.post("/sleep/nights", body)


@mcp.tool()
async def work_health(
    start: str | None = None,
    end: str | None = None,
    contract_hours: float = 35,
    with_days: bool = False,
) -> Any:
    """The work ↔ health file: work, legal landmarks, sleep, absences.

    Correlations (hours worked vs sleep the night after), nights after
    days off / short / long days, weeks, months, years, absences with the
    work and calls inside them, evidence. ``with_days`` adds every day.
    For the PDF: generate_report(report_type="work_health").
    """
    params = {"start": start, "end": end, "contract_hours": contract_hours}
    data = await client.get("/work/health", params)
    if not with_days and isinstance(data, dict):
        data.pop("days", None)
    return data
