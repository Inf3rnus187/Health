"""Async client for the Ollama HTTP API (vision + text).

One model per task, all configurable (§8): photos use the vision model,
medical documents the document model (defaults to the vision model,
which can also read scanned pages) and clinical reasoning the text
model. Tests monkeypatch these functions so no live Ollama is needed.
"""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Sequence
from typing import Any

import httpx

from app.core.config import get_settings

_settings = get_settings()

# Greedy decoding + a fixed seed: the same input always gives the same
# answer, so a re-analysis is reproducible (not a new dice roll). A wider
# context than Ollama's default so a whole lab report fits.
_OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 8192}
# One request at a time: a local model serves requests sequentially, so
# parallel worker jobs would only queue inside Ollama and hit timeouts
# (e.g. while re-analysing a whole photo history).
_GATE = asyncio.Semaphore(1)
_TIMEOUT = 600.0  # a 27B model reading a long report can be slow


def document_model() -> str:
    """Model used to read medical documents."""
    return _settings.ollama_document_model or _settings.ollama_vision_model


async def vision_json(
    prompt: str, image: bytes, *, model: str | None = None
) -> dict[str, Any]:
    """Return a strict-JSON description of ``image`` from a vision model."""
    return await generate_json(
        prompt, model or _settings.ollama_vision_model, images=[image]
    )


async def text_json(prompt: str, *, model: str | None = None) -> dict[str, Any]:
    """Return a strict-JSON answer from the text (reasoning) model."""
    return await generate_json(prompt, model or _settings.ollama_text_model)


async def generate_json(
    prompt: str, model: str, *, images: Sequence[bytes] = ()
) -> dict[str, Any]:
    """Run one deterministic JSON generation (optionally with images)."""
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": _OPTIONS,
    }
    if images:
        payload["images"] = [
            base64.b64encode(i).decode("ascii") for i in images
        ]
    async with _GATE, httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{_settings.ollama_url}/api/generate", json=payload
        )
        response.raise_for_status()
        body = response.json()
    return _parse(str(body.get("response", "{}")))


def _parse(text: str) -> dict[str, Any]:
    """Parse a model response that should be a JSON object."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}
