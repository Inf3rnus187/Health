"""Serialize tidy rows to CSV / JSON / XLSX / FHIR (§11)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from openpyxl import Workbook

from app.core.errors import InvalidInputError

_FIELDS = ["date", "metric_key", "value", "unit", "source"]
_XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument" ".spreadsheetml.sheet"
)


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    """Serialize rows as UTF-8 CSV."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, "value": _flatten(row.get("value"))})
    return buffer.getvalue().encode("utf-8")


def json_bytes(rows: list[dict[str, Any]]) -> bytes:
    """Serialize rows as a JSON array."""
    return json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")


def xlsx_bytes(rows: list[dict[str, Any]]) -> bytes:
    """Serialize rows as an XLSX workbook."""
    workbook = Workbook()
    sheet = workbook.active or workbook.create_sheet("data")
    sheet.append(_FIELDS)
    for row in rows:
        sheet.append([_flatten(row.get(field)) for field in _FIELDS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def fhir_bytes(rows: list[dict[str, Any]], user_id: str) -> bytes:
    """Serialize rows as a FHIR R4 Bundle of Observations."""
    entries = [_observation(row, user_id) for row in rows]
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries,
    }
    return json.dumps(bundle, ensure_ascii=False).encode("utf-8")


def render(
    fmt: str, rows: list[dict[str, Any]], user_id: str
) -> tuple[bytes, str, str]:
    """Return (bytes, media type, extension) for the requested format."""
    if fmt == "csv":
        return csv_bytes(rows), "text/csv", "csv"
    if fmt == "json":
        return json_bytes(rows), "application/json", "json"
    if fmt == "xlsx":
        return xlsx_bytes(rows), _XLSX_MIME, "xlsx"
    if fmt == "fhir":
        return fhir_bytes(rows, user_id), "application/fhir+json", "json"
    raise InvalidInputError(f"invalid format: {fmt}")


def _flatten(value: Any) -> Any:
    """Render dicts as compact JSON for tabular formats."""
    return (
        json.dumps(value, ensure_ascii=False)
        if isinstance(value, dict)
        else value
    )


def _observation(row: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Build one FHIR Observation entry from a tidy row."""
    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"text": row["metric_key"]},
        "effectiveDateTime": row["date"],
        "subject": {"reference": f"Patient/{user_id}"},
    }
    _set_value(resource, row.get("value"), row.get("unit"))
    return {"resource": resource}


def _set_value(resource: dict[str, Any], value: Any, unit: Any) -> None:
    """Attach a numeric or string value to an Observation."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        quantity: dict[str, Any] = {"value": value}
        if unit:
            quantity["unit"] = unit
        resource["valueQuantity"] = quantity
    elif value is not None:
        resource["valueString"] = str(value)
