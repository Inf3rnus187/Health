"""Tools: markers, weight / photo evolution, workouts, ECG, imports."""

from __future__ import annotations

from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def metabolic_markers() -> Any:
    """Validated markers with their bands and inputs.

    FibroScan CAP / E, WHtR, BMI, FLI, FIB-4, HbA1c, fasting glucose,
    TyG: value, band, inputs used, dates and history.
    """
    return await client.get("/evolution/markers")


@mcp.tool()
async def evolution_trend() -> Any:
    """Weight follow-up and long-term photo scores.

    Weight: latest, changes over 1/3/12 months, loss from the 12-month
    peak vs the 5/7/10/15 % milestones. Photos: scores per angle.
    """
    return await client.get("/evolution/trend")


@mcp.tool()
async def save_profile(
    waist_cm: float | None = None,
    height_cm: float | None = None,
    birth_year: int | None = None,
    cap_db_m: float | None = None,
    lsm_kpa: float | None = None,
    date_key: str | None = None,
) -> Any:
    """Record waist, height, birth year or a FibroScan (CAP dB/m, E kPa)."""
    body = {
        "waist_cm": waist_cm,
        "height_cm": height_cm,
        "birth_year": birth_year,
        "cap_db_m": cap_db_m,
        "lsm_kpa": lsm_kpa,
        "date_key": date_key,
    }
    return await client.post("/evolution/profile", body)


@mcp.tool()
async def list_photos(angle: str | None = None) -> Any:
    """Progress photos (face / profil / dos) with status and date."""
    return await client.get("/photos", {"angle": angle})


@mcp.tool()
async def photo_analysis(photo_id: str) -> Any:
    """A photo's analysis: quality control, scores, paired comparisons."""
    return await client.get(f"/photos/{photo_id}/analysis")


@mcp.tool()
async def analyze_photo(photo_id: str) -> Any:
    """Re-run the photo method on one photo (vision model)."""
    return await client.post(f"/photos/{photo_id}/analyze")


@mcp.tool()
async def reanalyze_all_photos() -> Any:
    """Re-run the photo method on the whole history (after a model change)."""
    return await client.post("/evolution/reanalyze-all")


@mcp.tool()
async def list_workouts(limit: int = 100, offset: int = 0) -> Any:
    """Workouts imported from Apple Health."""
    return await client.get("/workouts", {"limit": limit, "offset": offset})


@mcp.tool()
async def list_ecg() -> Any:
    """ECG recordings imported from Apple Health."""
    return await client.get("/ecg")


@mcp.tool()
async def list_routes() -> Any:
    """GPS routes (workouts) imported from Apple Health."""
    return await client.get("/routes")


@mcp.tool()
async def list_imports() -> Any:
    """Apple Health import jobs with their status and counts."""
    return await client.get("/imports")
