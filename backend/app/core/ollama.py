"""Async client for the Ollama HTTP API (vision + text).

The URL and models are configurable (§8). Tests monkeypatch these
functions so the pipeline runs without a live Ollama.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import httpx

from app.core.config import get_settings

_settings = get_settings()

# Greedy decoding + a fixed seed: the same image and prompt always give
# the same answer, so a re-analysis is reproducible (not a new dice roll).
_DETERMINISTIC = {"temperature": 0, "seed": 42}
# One request at a time: a local model serves requests sequentially, so
# parallel worker jobs would only queue inside Ollama and hit timeouts
# (e.g. while re-analysing a whole photo history).
_GATE = asyncio.Semaphore(1)


def _parse(text: str) -> dict[str, Any]:
    """Parse a model response that should be a JSON object."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


async def vision_json(
    prompt: str, image: bytes, *, model: str | None = None
) -> dict[str, Any]:
    """Return a strict-JSON description of ``image`` from a vision model."""
    payload = {
        "model": model or _settings.ollama_vision_model,
        "prompt": prompt,
        "images": [base64.b64encode(image).decode("ascii")],
        "stream": False,
        "format": "json",
        "options": _DETERMINISTIC,
    }
    async with _GATE, httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{_settings.ollama_url}/api/generate", json=payload
        )
        response.raise_for_status()
        body = response.json()
    return _parse(str(body.get("response", "{}")))
