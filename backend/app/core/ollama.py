"""Async client for the Ollama HTTP API (vision + text).

The URL and models are configurable (§8). Tests monkeypatch these
functions so the pipeline runs without a live Ollama.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from app.core.config import get_settings

_settings = get_settings()


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
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{_settings.ollama_url}/api/generate", json=payload
        )
        response.raise_for_status()
        body = response.json()
    return _parse(str(body.get("response", "{}")))
