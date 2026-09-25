"""What an update would bring, and the request to install it.

``./update.sh`` on the Docker host writes, in the folder shared with the
API: ``update.json`` (changes waiting, parts to rebuild), ``status.json``
(the last update) and ``heartbeat`` (cron runs it every minute). The page
reads them here. « Installer » only drops ``update-request`` in the same
folder; the host runs the update. The API never touches Docker or git.
"""

from __future__ import annotations

import json
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import ConflictError

#: The host's cron beat this recently: « Installer » can be offered.
FRESH_SECONDS = 180
#: A request not taken by then, or an update running longer, is stuck.
TAKEN_SECONDS = 180
RUNNING_SECONDS = 20 * 60
_PARTS = {"api": "API et worker", "web": "interface web", "mcp": "serveur MCP"}
_REQUEST = "update-request"
#: The host's copy of the request it took (it cannot delete the API's
#: file in a sticky run/ it does not own).
_TAKEN = "update-taken"


def state() -> dict[str, Any]:
    """Changes waiting, parts to rebuild, the last update, the watcher."""
    folder = Path(get_settings().update_dir)
    info = _read(folder / "update.json")
    last = _read(folder / "status.json")
    parts = [str(a) for a in info.get("areas", [])]
    requested = _pending(folder)
    watcher = _watching(folder)
    now = "requested" if requested else last.get("state", "idle")
    since = _since(folder, now, last)
    return {
        "known": bool(info),
        "behind": int(info.get("behind", 0) or 0),
        "commits": [str(c) for c in info.get("commits", [])][:20],
        "rebuild": [_PARTS.get(p, p) for p in parts],
        "checked_at": info.get("checked_at"),
        "current": info.get("current") or last.get("commit"),
        "latest": info.get("latest"),
        "watcher": watcher,
        "state": now,
        "since": since.isoformat(timespec="seconds") if since else None,
        "stalled": _stalled(now, since, watcher),
        "message": last.get("message", ""),
        "command": "./update.sh",
    }


def installed() -> dict[str, Any]:
    """The version the hub runs, for every page's header.

    The host's last update when it finished (all parts at that commit,
    even those it did not need to rebuild), else the commit it last saw,
    else the one the API was built from; ``installed_at``: when that
    update finished (None when unknown).
    """
    folder = Path(get_settings().update_dir)
    last = _read(folder / "status.json")
    done = last.get("state") == "done" and last.get("commit")
    info = _read(folder / "update.json")
    api = get_settings().git_commit or None
    return {
        "commit": (last.get("commit") if done else None)
        or info.get("current")
        or api,
        "installed_at": last.get("at") if done else None,
        "api": api,
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
    # Unique: the host tells a new request from the one it took by content.
    nonce = secrets.token_hex(4)
    try:
        (folder / _REQUEST).write_text(f"{stamp} {user_id} {nonce}\n")
    except OSError as exc:
        raise ConflictError(
            "Le dossier run/ n'est pas accessible en écriture : sur l'hôte, "
            "« chmod 1777 run »."
        ) from exc
    return state()


def _pending(folder: Path) -> bool:
    """A request dropped here that the host has not taken yet."""
    try:
        asked = (folder / _REQUEST).read_bytes()
    except OSError:
        return False
    try:
        return asked != (folder / _TAKEN).read_bytes()
    except OSError:
        return True


def _since(folder: Path, now: str, last: dict[str, Any]) -> datetime | None:
    """When the request was made, or the last update changed state."""
    if now == "requested":
        try:
            stamp = (folder / _REQUEST).stat().st_mtime
        except OSError:
            return None
        return datetime.fromtimestamp(stamp, UTC)
    try:
        return datetime.fromisoformat(str(last.get("at", "")))
    except ValueError:
        return None


def _stalled(now: str, since: datetime | None, watcher: bool) -> bool:
    """A request nobody takes, or an update that never ends.

    The host's cron takes a request within a minute; an update rebuilds
    in a few minutes. Past that, the page says so (and offers to ask
    again) instead of « en cours » for ever.
    """
    if since is None or now not in ("requested", "running"):
        return False
    age = (datetime.now(UTC) - since).total_seconds()
    if now == "requested":
        return not watcher or age > TAKEN_SECONDS
    return age > RUNNING_SECONDS


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
