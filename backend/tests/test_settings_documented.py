"""Every setting is documented where an operator looks for it."""

from __future__ import annotations

from pathlib import Path

from app.core.tuning import Tuning

ROOT = Path(__file__).resolve().parents[2]
#: Read by compose or nginx, not by the API.
OUTSIDE = [
    "API_TIMEOUT_S",
    "API_GRACEFUL_S",
    "API_KEEPALIVE_S",
    "WEB_MAX_BODY_MB",
    "WEB_API_TIMEOUT_S",
    "WEB_SYNC_TIMEOUT_S",
    "WEB_IMPORT_TIMEOUT_S",
    "WEB_GZIP_LEVEL",
    "WEB_GZIP_MIN_BYTES",
    "WEB_DNS_TTL_S",
    "WEB_PROXY_BUFFER_KB",
    "WEB_PROXY_BUFFERS",
    "WEB_PROXY_BUSY_KB",
    "WEB_ASSETS_CACHE_DAYS",
    "DB_SHARED_BUFFERS",
    "DB_EFFECTIVE_CACHE_SIZE",
    "DB_WORK_MEM",
    "DB_MAINTENANCE_WORK_MEM",
    "DB_SHM_SIZE",
]


def _names() -> list[str]:
    return [name.upper() for name in Tuning.model_fields] + OUTSIDE


def test_each_setting_is_in_the_guide_and_the_example() -> None:
    guide = (ROOT / "docs/guides/configuration.md").read_text()
    example = (ROOT / ".env.example").read_text()
    missing = [
        n for n in _names() if f"`{n}`" not in guide or f"{n}=" not in example
    ]
    assert missing == []


def test_the_web_server_values_reach_nginx() -> None:
    template = (ROOT / "nginx/default.conf.template").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    dockerfile = (ROOT / "nginx/Dockerfile").read_text()
    for name in (n for n in OUTSIDE if n.startswith("WEB_")):
        assert f"${{{name}}}" in template, name
        assert f"${{{name}:-" in compose, name
        assert f"{name}=" in dockerfile, name


def test_the_database_values_reach_postgresql() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()
    for name in (n for n in OUTSIDE if n.startswith("DB_")):
        assert f"${{{name}:-" in compose, name
