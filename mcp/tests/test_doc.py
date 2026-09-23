"""docs/mcp-tools.md is the reference generated from the server."""

from __future__ import annotations

from pathlib import Path

from phoenix_mcp import doc

_DOC = Path(__file__).resolve().parents[2] / "docs" / "mcp-tools.md"


async def test_tool_reference_is_up_to_date() -> None:
    """Regenerate with: python -m phoenix_mcp.doc > ../docs/mcp-tools.md."""
    assert _DOC.read_text(encoding="utf-8") == await doc.render()


async def test_every_tool_is_documented() -> None:
    page = await doc.render()
    assert page.count("\n### `") == len(await doc.mcp.list_tools())
