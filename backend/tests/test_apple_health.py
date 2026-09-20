"""Apple Health import: raw storage, roll-ups, ECG/routes, API, reset."""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from app.core.db import SessionFactory
from app.models.user import User
from app.services import imports
from app.services.apple_health.units import convert
from httpx import AsyncClient
from sqlalchemy import select

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
IMPORTS = "/api/v1/imports"

_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<!DOCTYPE HealthData [\n<!ELEMENT HealthData (Record*, Workout*)>\n]>\n"
    '<HealthData locale="fr_FR">\n'
)


def _rec(rtype: str, value: str, unit: str, start: str, end: str) -> str:
    return (
        f'<Record type="{rtype}" unit="{unit}" value="{value}" '
        f'sourceName="Watch" startDate="{start}" endDate="{end}"/>\n'
    )


def _export_xml() -> str:
    d = "2026-03-02 08:00:00 +0000"
    step = "HKQuantityTypeIdentifierStepCount"
    hr = "HKQuantityTypeIdentifierHeartRate"
    body = (
        _rec(step, "10", "count", d, d)
        + _rec(step, "5", "count", d, d)
        + _rec(hr, "55", "count/min", d, d)
        + _rec(hr, "80", "count/min", d, d)
        + _rec(hr, "150", "count/min", d, d)
        + _rec("HKQuantityTypeIdentifierBodyMass", "190", "lb", d, d)
        + _rec("HKQuantityTypeIdentifierOxygenSaturation", "0.97", "%", d, d)
        + _sleep()
        + _workout()
    )
    return _HEADER + body + "</HealthData>\n"


def _sleep() -> str:
    return (
        '<Record type="HKCategoryTypeIdentifierSleepAnalysis" '
        'value="HKCategoryValueSleepAnalysisAsleepDeep" '
        'startDate="2026-03-01 23:50:00 +0000" '
        'endDate="2026-03-02 00:20:00 +0000"/>\n'
    )


def _workout() -> str:
    return (
        '<Workout workoutActivityType="HKWorkoutActivityTypeRunning" '
        'duration="30" durationUnit="min" '
        'totalDistance="6" totalDistanceUnit="km" '
        'totalEnergyBurned="420" totalEnergyBurnedUnit="kcal" '
        'startDate="2026-03-02 18:00:00 +0000" '
        'endDate="2026-03-02 18:30:00 +0000"/>\n'
    )


_ECG = (
    "Nom,Test\n"
    "Enregistré le,2026-03-02 06:15:00 +0100\n"
    "Classification,Rythme sinusal\n"
    "Fréquence d'échantillonnage,512 Hz\n"
    ",\n-10\n-12\n-8\n"
)

_ECG_POOR = (
    "Classification,Mauvais enregistrement\n"
    "Fréquence d'échantillonnage,512 Hz\n"
    ",\n1\n2\n3\n"
)

_GPX = (
    '<?xml version="1.0"?><gpx>'
    "<metadata><time>2030-01-01T00:00:00Z</time></metadata>"
    "<trk><trkseg>"
    '<trkpt lat="1" lon="2"><time>2026-03-02T17:18:00Z</time></trkpt>'
    '<trkpt lat="1" lon="2"><time>2026-03-02T17:18:05Z</time></trkpt>'
    "</trkseg></trk></gpx>"
)

_CDA = (
    '<?xml version="1.0"?>\n'
    '<ClinicalDocument xmlns="urn:hl7-org:v3" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<title>Résumé</title><component><structuredBody><component>"
    "<section><entry><observation>"
    '<code code="2339-0" displayName="Glucose" codeSystemName="LOINC"/>'
    '<effectiveTime value="20260115"/>'
    '<value xsi:type="PQ" value="5.4" unit="mmol/L"/>'
    "</observation></entry></section>"
    "</component></structuredBody></component></ClinicalDocument>"
)


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    root = "apple_health_export"
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{root}/export.xml", _export_xml())
        archive.writestr(f"{root}/export_cda.xml", _CDA)
        archive.writestr(f"{root}/electrocardiograms/ecg_1.csv", _ECG)
        archive.writestr(f"{root}/electrocardiograms/ecg_bad.csv", _ECG_POOR)
        archive.writestr(f"{root}/workout-routes/route_1.gpx", _GPX)
    return buffer.getvalue()


_CSV_HEAD = (
    "type,sourceName,sourceVersion,productType,device,"
    "startDate,endDate,unit,value\n"
)
_DEV = '"<<HKDevice: 0x1>, name:Apple Watch, model:Watch>"'


def _csv_row(hk: str, unit: str, value: str) -> str:
    d = "2026-03-02 08:00:00 +0000"
    return f"{hk},Apple Watch,26.2,Watch7,{_DEV},{d},{d},{unit},{value}\n"


def _csv_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    step = "HKQuantityTypeIdentifierStepCount"
    mass = "HKQuantityTypeIdentifierBodyMass"
    steps_csv = (
        _CSV_HEAD + _csv_row(step, "count", "10") + _csv_row(step, "count", "5")
    )
    mass_csv = _CSV_HEAD + _csv_row(mass, "kg", "86.2")
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{step}_SimpleHealthExportCSV.csv", steps_csv)
        archive.writestr(f"{mass}_SimpleHealthExportCSV.csv", mass_csv)
    return buffer.getvalue()


async def test_csv_zip_import(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """A SimpleHealthExportCSV zip imports like the XML export."""
    response = await client.post(
        f"{IMPORTS}/apple-health",
        files={"file": ("csv.zip", _csv_zip_bytes(), "application/zip")},
        headers=auth,
    )
    job_id = response.json()["id"]
    await _run(job_id)
    job = (await client.get(f"{IMPORTS}/{job_id}", headers=auth)).json()
    assert job["status"] == "done"
    assert job["samples"] == 3
    steps = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "activity.steps"},
        headers=auth,
    )
    assert steps.json()[0]["value"] == 15.0
    mass = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "body.weight"},
        headers=auth,
    )
    assert mass.json()[0]["value"] == 86.2


async def _admin_id() -> str:
    async with SessionFactory() as session:
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        return result.scalar_one().id


async def _upload(client: AsyncClient, auth: dict[str, str]) -> str:
    response = await client.post(
        f"{IMPORTS}/apple-health",
        files={"file": ("export.zip", _zip_bytes(), "application/zip")},
        headers=auth,
    )
    assert response.status_code == 202
    return response.json()["id"]


async def _run(job_id: str) -> None:
    async with SessionFactory() as session:
        await imports.run_job(session, job_id)


def test_unit_conversion() -> None:
    assert convert(2.0, "mi", "km") == 2.0 * 1.609344
    assert convert(0.97, "%", "%") == 97.0
    assert convert(212.0, "degF", "°C") == 100.0


async def test_upload_stores_all_raw_samples(
    tmp_path: Path, client: AsyncClient, auth: dict[str, str]
) -> None:
    job_id = await _upload(client, auth)
    await _run(job_id)
    job = (await client.get(f"{IMPORTS}/{job_id}", headers=auth)).json()
    assert job["status"] == "done"
    assert job["samples"] == 8
    assert job["workouts"] == 1 and job["ecg"] == 1 and job["routes"] == 1
    steps = await client.get(
        "/api/v1/samples", params={"metric_key": "activity.steps"}, headers=auth
    )
    assert steps.json()["total"] == 2


async def test_rollups_and_records(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _run(await _upload(client, auth))
    daily = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "activity.steps"},
        headers=auth,
    )
    assert daily.json()[0]["value"] == 15.0
    workouts = await client.get("/api/v1/workouts", headers=auth)
    assert len(workouts.json()) == 1
    ecg = await client.get("/api/v1/ecg", headers=auth)
    assert ecg.json()[0]["classification"] == "Rythme sinusal"
    routes = await client.get("/api/v1/routes", headers=auth)
    assert routes.json()[0]["point_count"] == 2


async def test_ecg_and_route_viewers(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _run(await _upload(client, auth))
    ecg = (await client.get("/api/v1/ecg", headers=auth)).json()
    series = await client.get(
        f"/api/v1/ecg/{ecg[0]['id']}/series", headers=auth
    )
    assert series.json()["values"] == [-10.0, -12.0, -8.0]
    routes = (await client.get("/api/v1/routes", headers=auth)).json()
    track = await client.get(
        f"/api/v1/routes/{routes[0]['id']}/track", headers=auth
    )
    assert len(track.json()["points"]) == 2
    # started_at is the first track point, not the export <metadata> time.
    assert routes[0]["started_at"].startswith("2026-03-02")


async def test_poor_ecg_skipped(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _run(await _upload(client, auth))
    ecg = (await client.get("/api/v1/ecg", headers=auth)).json()
    labels = [row["classification"] for row in ecg]
    assert "Mauvais enregistrement" not in labels
    assert len(ecg) == 1


async def test_import_cda_observations(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _run(await _upload(client, auth))
    obs = await client.get("/api/v1/clinical/observations", headers=auth)
    body = obs.json()
    assert body["total"] == 1
    assert body["items"][0]["label"] == "Glucose"
    assert body["items"][0]["value_num"] == 5.4
    doc = await client.get("/api/v1/clinical/document", headers=auth)
    assert doc.json()["observation_count"] == 1


async def test_reimport_is_idempotent(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _run(await _upload(client, auth))
    await _run(await _upload(client, auth))
    hr = await client.get(
        "/api/v1/samples", params={"metric_key": "heart.rate"}, headers=auth
    )
    assert hr.json()["total"] == 3


async def test_reset_wipes_imported(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _run(await _upload(client, auth))
    cleared = await client.post(f"{IMPORTS}/reset", headers=auth)
    assert cleared.status_code == 200
    listed = await client.get("/api/v1/samples", headers=auth)
    assert listed.json()["total"] == 0
    assert (await client.get("/api/v1/ecg", headers=auth)).json() == []
