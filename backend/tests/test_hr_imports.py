"""HR and tool exports: expense report PDFs, ticket exports, absences."""

from __future__ import annotations

import json
from typing import Any

from app.services import expense_report_read
from fpdf import FPDF
from httpx import AsyncClient

TRACES = "/api/v1/traces/import"
ABSENCES = "/api/v1/absences/import"


def _lines(pdf: FPDF, texts: tuple[str, ...]) -> None:
    for text in texts:
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")


def _archived_report() -> bytes:
    """Like a Lucca archive: a summary, then a page per expense."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=10)
    pdf.add_page()
    _lines(pdf, ("Note de Frais n°7", "Mars 2026", "Déclarant",
                 "Alex TESTEUR", "Date de déclaration",
                 "20/03/2026 10:20:00"))  # fmt: skip
    for number, day, nature, vendor, comment, amount in (
        ("1", "02/03/2026", "Taxi", "Uber B.V.", "Retour tardif", "31,20"),
        ("2", "05/03/2026", "Hôtel", "Hôtel Test", "Nuit d'astreinte", "89,50"),
    ):
        pdf.add_page()
        _lines(pdf, (f"Dépense #{number}", nature, "Date de la dépense", day,
                     "Commentaires", comment, "Fournisseur", vendor,
                     "Source", "Justificatif scanné", "Montants TTC",
                     f"Dépensé {amount} EUR"))  # fmt: skip
    return bytes(pdf.output())


def _printed_report() -> bytes:
    """Like a printed report: one table, comments numbered below."""
    pdf = FPDF(orientation="L")
    pdf.set_font("Helvetica", size=9)
    pdf.add_page()
    _lines(pdf, ("NDF #7 : Mars 2026, déclarée le 20/03/2026",
                 "Imprimé le 02/04/2026 à 11:13",
                 "Déclarant : TESTEUR Alex"))  # fmt: skip
    columns = (10, 30, 60, 100, 150, 190, 215, 235, 260)
    for row in (
        ("N°", "Date", "Nature", "Fournisseur", "Centre", "Montant", "Devise",
         "TTC", "Refact."),
        ("1", "02/03/2026", "Taxi", "Uber B.V.", "DEV", "31,20 EUR", "EUR",
         "31,20 EUR", "Non (1)"),
        ("3", "09/03/2026", "Autres frais", "Test Cloud LLC", "DEV",
         "20,00 $", "USD", "18,40 EUR", "Non (2)"),
    ):  # fmt: skip
        y = pdf.get_y()
        for x, text in zip(columns, row, strict=True):
            pdf.set_xy(x, y)
            pdf.cell(20, 7, text)
        pdf.ln(8)
    _lines(pdf, ("Commentaires :", "(1) Retour tardif",
                 "(2) Abonnement outil"))  # fmt: skip
    return bytes(pdf.output())


async def _post(
    client: AsyncClient,
    auth: dict[str, str],
    url: str,
    files: list[tuple[str, bytes]],
    **fields: Any,
) -> Any:
    params = {"dry_run": str(fields.pop("dry_run", False)).lower()}
    data: dict[str, Any] = {"person": fields.pop("person", "")}
    if url == TRACES:
        data["kinds"] = [fields.pop("kind", "auto")] * len(files)
    res = await client.post(
        url,
        files=[
            ("files", (name, raw, "application/octet-stream"))
            for name, raw in files
        ],  # fmt: skip
        data=data,
        params=params,
        headers=auth,
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_a_printed_expense_report_table_is_read() -> None:
    data = _printed_report()
    text = expense_report_read.text_of(data)
    assert expense_report_read.is_report(text)
    report = expense_report_read.read(data, text)
    assert report.label == "Note de frais n°7 — Mars 2026"
    assert report.issued is not None and report.timed
    assert f"{report.issued:%d/%m %H:%M}" == "02/04 11:13"  # printed
    taxi, other = report.lines
    assert (taxi.nature, taxi.vendor) == ("Taxi", "Uber B.V.")
    assert taxi.amount == 31.2
    assert taxi.comment == "Retour tardif"
    assert (other.vendor, other.amount, other.paid) == (
        "Test Cloud LLC", 18.4, "20,00 $",
    )  # fmt: skip


async def test_an_expense_report_gives_its_lines_and_keeps_the_pdf(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    rides = (
        "Request Time,Begin Trip Time,Dropoff Time,Fare Amount,Fare Currency\n"
        "2026-03-02 22:31:00 +0000 UTC,2026-03-02 22:40:00 +0000 UTC,"
        "2026-03-02 23:05:00 +0000 UTC,31.20,EUR\n"
    )
    await _post(
        client, auth, TRACES, [("trips_data.csv", rides.encode())], kind="taxi"
    )
    pdf = _archived_report()
    first = await _post(client, auth, TRACES, [("ndf-7.pdf", pdf)])
    counts = first["files"][0]
    assert counts["columns"] == {
        "document": "Note de frais n°7 — Mars 2026 : 2 dépenses"
    }
    assert (counts["new"], counts["merged"]) == (2, 1)  # PDF + hotel; ride
    again = await _post(client, auth, TRACES, [("ndf-7.pdf", pdf)])
    assert again["files"][0]["duplicates"] == 3
    items = (await client.get("/api/v1/evidence", headers=auth)).json()
    kept = next(i for i in items if i["kind"] == "document")
    assert kept["file_name"] == "ndf-7.pdf" and kept["sha256"]
    assert kept["title"] == "Note de frais n°7 — Mars 2026"
    ride = next(i for i in items if i["kind"] == "taxi")
    assert ride["time_known"]  # the ride keeps its time (23:31 Paris)
    assert "Retour tardif" in ride["description"]  # the report's comment
    hotel = next(i for i in items if i["kind"] == "hotel")
    assert not hotel["time_known"] and hotel["amount"] == 89.5


_TICKETS = "\n".join((
    '\ufeff"Statut","Id","Objet","Créé","Commentaire créé",'
    '"Utilisateur de commentaires","Visibilité de commentaires",'
    '"Heure de début du commentaire","Commentaire"',
    '"Fermé","101","Imprimante HS","02/03/2026 08:00",,,,,',
    ',,,,"02/03/2026 08:40","Alex Martin","Public","02/03/2026 08:12","Vu"',
    ',,,,"02/03/2026 09:00","Sam Dupont","Public",,"Merci ""vite"" !"',
    '"Fermé","102","Serveur lent","02/03/2026 20:00",,,,,',
    ',,,,"02/03/2026 23:10","Alex Martin","Privé",,"Redémarré',
    'après sauvegarde"',
    ',,,,"03/03/2026 07:45","Alex Martin","Public",,"Suivi"',
)) + "\n"  # fmt: skip


async def test_a_ticket_export_gives_a_day_of_actions(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    raw = _TICKETS.encode()
    preview = await _post(
        client, auth, TRACES, [("Tous_les_tickets.csv", raw)], dry_run=True
    )
    about = preview["files"][0]["columns"]
    assert about["person"] == "Alex Martin"  # the most active author
    assert about["people"] == [
        {"name": "Alex Martin", "actions": 3},
        {"name": "Sam Dupont", "actions": 1},
    ]
    done = await _post(client, auth, TRACES, [("t.csv", raw)])
    assert done["files"][0]["new"] == 2  # two days
    again = await _post(client, auth, TRACES, [("t.csv", raw)])
    assert again["files"][0]["duplicates"] == 2
    items = (await client.get("/api/v1/evidence", headers=auth)).json()
    day = next(i for i in items if i["occurred_at"].startswith("2026-03-02"))
    assert day["kind"] == "activite" and day["count"] == 2
    assert day["occurred_at"].startswith("2026-03-02T07:12")  # 08:12 Paris
    assert day["ended_at"].startswith("2026-03-02T22:10")  # 23:10 Paris
    assert "23:10 #102 Serveur lent (privé)" in day["description"]
    assert "Sam Dupont" not in day["description"]


_ABSENCES = (
    "Collaborateur;Date de début;Date de fin;Compte;Statut;Commentaire\n"
    "Alex Martin;03/04/2026;03/04/2026;RTT;Approuvée;\n"
    "Alex Martin;06/04/2026;10/04/2026;Congés payés;Approuvée;Vacances\n"
    "Alex Martin;14/04/2026;17/04/2026;Maladie;Approuvée;\n"
    "Alex Martin;20/04/2026;20/04/2026;Congés payés;Refusée;\n"
    "Alex Martin;21/04/2026;21/04/2026;Télétravail;Approuvée;\n"
    "Sam Dupont;03/04/2026;03/04/2026;RTT;Approuvée;\n"
)


async def test_absences_come_from_an_hr_export(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    raw = _ABSENCES.encode()
    preview = await _post(
        client, auth, ABSENCES, [("absences.csv", raw)], dry_run=True
    )
    read = preview["files"][0]
    assert read["columns"]["person"] == "Alex Martin"
    assert [(p["start"], p["kind"]) for p in read["preview"]] == [
        ("2026-04-03", "repos"),
        ("2026-04-06", "conge"),
        ("2026-04-14", "arret_maladie"),
    ]
    assert read["skipped_count"] == 2  # refused, remote work
    assert (await _post(client, auth, ABSENCES, [("a.csv", raw)]))["files"][0][
        "new"
    ] == 3
    again = await _post(client, auth, ABSENCES, [("a.csv", raw)])
    assert again["files"][0]["duplicates"] == 3
    rows = (await client.get("/api/v1/absences", headers=auth)).json()
    assert [r["kind"] for r in rows] == ["repos", "conge", "arret_maladie"]
    assert rows[1]["note"] == "Import : Congés payés ; Vacances"


async def test_absences_one_day_per_record_are_joined(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Like an HR API: one record per half day, a weekend in between."""
    days = ("2026-04-09", "2026-04-10", "2026-04-13")
    items = [
        {"date": f"{d}T00:00:00", "isAM": am,
         "leaveAccount": {"name": "Congés payés"}}
        for d in days
        for am in (True, False)
    ]  # fmt: skip
    raw = json.dumps({"data": {"items": items}}).encode()
    read = await _post(client, auth, ABSENCES, [("leaves.json", raw)])
    (period,) = read["files"][0]["preview"]
    assert (period["start"], period["end"]) == ("2026-04-09", "2026-04-13")
    assert period["kind"] == "conge"


async def test_half_days_in_an_hr_export(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    rows = (
        "Date de début;Début;Date de fin;Fin;Compte\n"
        "07/05/2026;Après-midi;11/05/2026;Matin;Congés payés\n"
    )
    read = await _post(client, auth, ABSENCES, [("a.csv", rows.encode())])
    (period,) = read["files"][0]["preview"]
    assert (period["start_half"], period["end_half"]) == ("pm", "am")
    halves = [
        {"date": f"2026-06-{d}T00:00:00", "isAM": am,
         "leaveAccount": {"name": "RTT"}}
        for d, am in (("01", True), ("01", False), ("02", True))
    ]  # fmt: skip
    raw = json.dumps({"data": {"items": halves}}).encode()
    read = await _post(client, auth, ABSENCES, [("rtt.json", raw)])
    (rtt,) = read["files"][0]["preview"]
    assert (rtt["start"], rtt["end"], rtt["end_half"]) == (
        "2026-06-01", "2026-06-02", "am",
    )  # fmt: skip
    listed = (await client.get("/api/v1/absences", headers=auth)).json()
    assert [a["days"] for a in listed] == [4.0, 1.5]
