#!/usr/bin/env bash
# ============================================================================
# Phoenix Health Hub — one-shot bootstrap: build, migrate, seed, start.
# Usage: cp .env.example .env  (optional; created for you)  then  ./install.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

info() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required but was not found on PATH." >&2
    exit 1
fi

# 1. Create .env with a strong random SECRET_KEY on first run.
if [ ! -f .env ]; then
    info "Creating .env from .env.example"
    cp .env.example .env
    if command -v python3 >/dev/null 2>&1; then
        SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    else
        SECRET="$(openssl rand -base64 48 | tr -d '\n/+=')"
    fi
    sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env && rm -f .env.bak
    info "Generated a random SECRET_KEY. Review .env and set your passwords."
fi

# Where ./update.sh and the web page exchange update status and requests
# (the API runs as uid 10001: the folder is writable by all, sticky).
mkdir -p run && chmod 1777 run

# 2. Build all images.
info "Building images"
docker compose build

# 3. Start data services and wait for them to become healthy.
info "Starting database and cache"
docker compose up -d db redis

# 4. Apply migrations and seed the catalogue + admin (idempotent).
info "Applying migrations and seeding the metric catalogue"
docker compose run --rm api python -m app.seed.seed

# 5. Bring the whole stack up.
info "Starting the full stack"
docker compose up -d

WEB_PORT="$(grep -E '^WEB_PORT=' .env | cut -d= -f2 || true)"
info "Ready. Open http://localhost:${WEB_PORT:-8082}  (API docs at /api/v1/docs)"
info "Updates: ./update.sh (now) ; ./update.sh --install-cron (the page's « Installer » button)"
