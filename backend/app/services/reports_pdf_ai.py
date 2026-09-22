"""The AI clinical synthesis in the PDF report, with its facts annex."""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

from app.services.pdf_text import heading, line

_WARNING = (
    "Redigee par le modele medical local ({model}) a partir des seules "
    "donnees du dossier listees en annexe (references [F..]). Chaque "
    "phrase cite ses faits ; une phrase sans reference ou avec un chiffre "
    "absent de ses faits a ete retiree ({rejected}). A valider par un "
    "medecin : ce n'est ni un diagnostic ni une prescription."
)


def synthesis(pdf: FPDF, found: dict[str, Any] | None) -> None:
    """Write the synthesis sections (nothing without a synthesis)."""
    if not found:
        return
    heading(pdf, "Synthese clinique (IA, verifiee sur le dossier)", 13)
    if found.get("error"):
        line(pdf, 6, f"Synthese indisponible : {found['error']}")
        pdf.ln(2)
        return
    pdf.set_font("Helvetica", "I", 8)
    line(pdf, 4, _WARNING.format(**_meta(found)))
    pdf.set_font("Helvetica", size=10)
    for section in found.get("sections", []):
        if section["items"]:
            _section(pdf, section)
    pdf.ln(2)


def facts(pdf: FPDF, found: dict[str, Any] | None) -> None:
    """Append the numbered facts the synthesis could use."""
    if not found or not found.get("facts"):
        return
    pdf.add_page()
    heading(pdf, "Annexe - faits du dossier utilises par la synthese")
    pdf.set_font("Helvetica", size=8)
    for fact in found["facts"]:
        line(pdf, 4.5, f"[{fact['id']}] {fact['section']} - {fact['text']}")


def _section(pdf: FPDF, section: dict[str, Any]) -> None:
    """One titled list of sentences with their fact references."""
    pdf.set_font("Helvetica", "B", 10)
    line(pdf, 7, section["title"])
    pdf.set_font("Helvetica", size=10)
    for item in section["items"]:
        refs = "".join(f"[{ref}]" for ref in item["facts"])
        line(pdf, 5.5, f"- {item['text']} {refs}".rstrip())


def _meta(found: dict[str, Any]) -> dict[str, Any]:
    """Model name and rejected count for the warning line."""
    return {
        "model": found.get("model", "?"),
        "rejected": found.get("rejected", 0),
    }
