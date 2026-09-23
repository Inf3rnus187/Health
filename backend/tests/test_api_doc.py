"""docs/api.md is the reference generated from the live routes."""

from __future__ import annotations

from pathlib import Path

from app.cli import api_doc
from app.main import app

_DOC = Path(__file__).resolve().parents[2] / "docs" / "api.md"


def test_api_reference_is_up_to_date() -> None:
    """Regenerate with: python -m app.cli.api_doc > ../docs/api.md."""
    assert _DOC.read_text(encoding="utf-8") == api_doc.render(app)


def test_reference_reads_the_real_access_rules() -> None:
    page = api_doc.render(app)
    assert "| GET | `/export` | `read:all` |" in page
    assert "| POST | `/tokens` | Session uniquement |" in page
    assert "| GET | `/medical/record` | Session / hub:full |" in page
    assert "| POST | `/auth/login` | Public |" in page
