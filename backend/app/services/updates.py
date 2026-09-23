"""What an update would bring, and the request to install it.

``./update.sh`` on the Docker host writes, in the folder shared with the
API: ``update.json`` (changes waiting, parts to rebuild), ``status.json``
(the last update) and ``heartbeat`` (cron runs it every minute). The page
reads them here. « Installer » only drops ``update-request`` in the same
folder; the host runs the update. The API never touches Docker or git.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import ConflictError

#: The host's cron beat this recently: « Installer » can be offered.
FRESH_SECONDS = 180
_PARTS = {"api": "API et worker", "web": "interface web", "mcp": "serveur MCP"}
_REQUEST = "update-request"


def state() -> dict[str, Any]:
    """Changes waiting, parts to rebuild, the last update, the watcher."""
    folder = Path(get_settings().update_dir)
    info = _read(folder / "update.json")
    last = _read(folder / "status.json")
    parts = [str(a) for a in info.get("areas", [])]
    requested = (folder / _REQUEST).exists()
    return {
        "known": bool(info),
        "behind": int(info.get("behind", 0) or 0),
        "commits": [str(c) for c in info.get("commits", [])][:20],
        "rebuild": [_PARTS.get(p, p) for p in parts],
        "checked_at": info.get("checked_at"),
        "current": info.get("current") or last.get("commit"),
        "latest": info.get("latest"),
        "watcher": _watching(folder),
        "state": "requested" if requested else last.get("state", "idle"),
        "message": last.get("message", ""),
        "command": "./update.sh",
    }


def request(user_id: str) -> dict[str, Any]:
    """Ask the host to update (its cron runs ./update.sh within a minute)."""
    folder = Path(get_settings().update_dir)
    if not _watching(folder):
        raise ConflictError(
            "La mise à jour automatique n'est pas active sur l'hôte : dans "
            "le dossier du hub, lancer ./update.sh (ou ./update.sh "
            "--install-cron pour ce bouton)."
        )
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        (folder / _REQUEST).write_text(f"{stamp} {user_id}\n")
    except OSError as exc:
        raise ConflictError(
            "Le dossier run/ n'est pas accessible en écriture : sur l'hôte, "
            "« chmod 1777 run »."
        ) from exc
    return state()


def _watching(folder: Path) -> bool:
    """Whether the host's cron ran ./update.sh --cron lately."""
    try:
        beat = int((folder / "heartbeat").read_text().strip() or 0)
    except (OSError, ValueError):
        return False
    return time.time() - beat < FRESH_SECONDS


def _read(path: Path) -> dict[str, Any]:
    """A JSON file of the shared folder ({} when absent or unreadable)."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
