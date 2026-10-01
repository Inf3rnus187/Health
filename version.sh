#!/usr/bin/env bash
# ============================================================================
# Phoenix Health Hub — which code runs right now, before reading any log.
#
#   ./version.sh    the commit on disk (date, title), the commit the API and
#                   the worker were started with (GIT_COMMIT, given by
#                   ./update.sh), the database's migration and the last
#                   update; a warning when the running server code is not
#                   the code on disk (an update of the docs or the page
#                   alone leaves the API on its older commit: same code).
#
# Put it in front of a diagnostic command (./version.sh && docker compose
# logs api …) to know which code the lines come from. It only reads:
# nothing is changed. POSTGRES_USER / POSTGRES_DB come from .env.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")" || exit 1
COMPOSE="${COMPOSE:-docker compose}"

env_value() {  # NAME default: its value in .env, else the default
    local found
    found="$(sed -n "s/^$1=//p" .env 2>/dev/null | tail -1)"
    printf '%s' "${found:-$2}"
}

running() {  # service: the commit it was started with, else « inconnu »
    local found
    found="$($COMPOSE exec -T "$1" printenv GIT_COMMIT 2>/dev/null | tr -d '\r')"
    printf '%s' "${found:-inconnu}"
}

migration() {  # the database's Alembic revision, else « inconnue »
    local found
    found="$($COMPOSE exec -T db psql -U "$(env_value POSTGRES_USER phoenix)" \
        -d "$(env_value POSTGRES_DB phoenix)" -tAc \
        'select version_num from alembic_version' 2>/dev/null | tr -d '\r')"
    printf '%s' "${found:-inconnue}"
}

last_update() {  # « commit (state) » of run/status.json, else « aucune »
    local found
    found="$(sed -n 's/.*"state": "\([a-z]*\)".*"commit": "\([0-9a-f]*\)".*/\2 (\1)/p' \
        run/status.json 2>/dev/null)"
    printf '%s' "${found:-aucune}"
}

same_code() {  # commit: no server file changed between it and the disk
    [ "$1" != inconnu ] && git diff --quiet "$1" HEAD -- backend \
        docker-compose.yml 2>/dev/null
}

main() {
    local disk api worker
    disk="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
    api="$(running api)"
    worker="$(running worker)"
    echo "Dépôt   : $(git log -1 --date=format-local:'%d/%m/%Y %H:%M' \
        --format='%h du %cd — %s' 2>/dev/null || echo '?')"
    echo "Tourne  : API $api · worker $worker"
    echo "Base    : migration $(migration)"
    echo "Mise à jour : $(last_update)"
    if same_code "$api" && same_code "$worker"; then
        echo "✓ L'API et le worker tournent avec le code serveur du dépôt"
    else
        echo "⚠ L'API ou le worker ne tourne pas avec le code serveur du" \
            "dépôt ($disk) : lancer ./update.sh"
    fi
    echo "----"
}

main "$@"; exit
