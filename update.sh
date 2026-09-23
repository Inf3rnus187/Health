#!/usr/bin/env bash
# ============================================================================
# Phoenix Health Hub — update from git, rebuild only what changed.
#
#   ./update.sh                 pull and rebuild now (instead of the manual
#                               git pull && docker compose up -d --build …)
#   ./update.sh --check         fetch; write what an update would bring
#                               (run/update.json, read by the web page)
#   ./update.sh --cron          for cron, every minute: check GitHub every
#                               15 min, run the update asked for on the page
#   ./update.sh --install-cron  add that cron line for the current user
#   … --auto                    (with --cron / --install-cron) also install
#                               a waiting update by itself, without the click
#
# The web page never touches Docker: its « Installer » button only drops
# run/update-request; this script, run by you or by cron on the host,
# does the work. `git pull --ff-only`: local changes or a diverged
# history stop the update (nothing overwritten). .env and the data
# volumes are never touched; migrations run when the API starts.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"
# cron starts with a bare PATH: find docker where NAS and distros put it.
export PATH="$PATH:/usr/local/bin:/usr/bin:/bin:/snap/bin"
# git must never wait for a password under cron (it would hang).
export GIT_TERMINAL_PROMPT=0

RUN="run"
COMPOSE="${COMPOSE:-docker compose}"
CHECK_EVERY=900

mkdir -p "$RUN"
chmod 1777 "$RUN" 2>/dev/null || true  # the API (uid 10001) drops requests

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

json_text() {  # a string as JSON (quotes, backslashes, controls escaped)
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\000-\037'
}

status() {  # state message
    printf '{"state": "%s", "message": "%s", "at": "%s", "commit": "%s"}\n' \
        "$1" "$(json_text "$2")" "$(now)" "$(git rev-parse --short HEAD)" \
        > "$RUN/status.json.tmp" && mv "$RUN/status.json.tmp" "$RUN/status.json"
}

areas() {  # the parts to rebuild for the files changed between $1 and $2
    git diff --name-only "$1" "$2" | awk '
        /^backend\//              { a["api"] = 1 }
        /^(frontend|nginx)\//     { a["web"] = 1 }
        /^mcp\//                  { a["mcp"] = 1 }
        /^docker-compose\.ya?ml$/ { a["api"] = 1; a["web"] = 1; a["mcp"] = 1 }
        END { n = 0; for (k in a) printf "%s%s", (n++ ? " " : ""), k }'
}

check() {
    git fetch --quiet
    local behind commits list=""
    behind="$(git rev-list --count HEAD..@{u})"
    commits="$(git log --format='%h %s' HEAD..@{u} | head -n 20)"
    while IFS= read -r line; do
        [ -n "$line" ] && list="$list\"$(json_text "$line")\", "
    done <<< "$commits"
    local parts=""
    for part in $(areas HEAD @{u}); do parts="$parts\"$part\", "; done
    printf '{"behind": %s, "commits": [%s], "areas": [%s], "checked_at": "%s", "current": "%s", "latest": "%s"}\n' \
        "$behind" "${list%, }" "${parts%, }" "$(now)" \
        "$(git rev-parse --short HEAD)" "$(git rev-parse --short @{u})" \
        > "$RUN/update.json.tmp" && mv "$RUN/update.json.tmp" "$RUN/update.json"
    echo "$behind change(s) waiting; to rebuild: $(areas HEAD @{u})"
}

mcp_running() {
    [ -n "$($COMPOSE --profile mcp ps -q mcp 2>/dev/null || true)" ]
}

rebuild() {  # the services behind the parts changed
    local parts="$1" services=""
    case "$parts" in *api*) services="$services api worker" ;; esac
    case "$parts" in *web*) services="$services web" ;; esac
    if [ -n "$services" ]; then
        # shellcheck disable=SC2086
        $COMPOSE up -d --build $services
    fi
    case "$parts" in
        *mcp*) if mcp_running; then $COMPOSE --profile mcp up -d --build mcp; fi ;;
    esac
}

update() {
    status running "Mise à jour en cours"
    local before
    before="$(git rev-parse HEAD)"
    if ! git pull --ff-only --quiet; then
        status failed "git pull impossible (modifications locales ou historique divergent) : voir « git status » sur l'hôte"
        return 1
    fi
    local parts
    parts="$(areas "$before" HEAD)"
    if ! rebuild "$parts"; then
        status failed "La reconstruction a échoué : voir run/update.log sur l'hôte"
        return 1
    fi
    status done "À jour ($(git rev-parse --short HEAD)) ; reconstruit : ${parts:-rien (documentation seulement)}"
    check >/dev/null
}

cron() {
    date -u +%s > "$RUN/heartbeat"
    exec 9> "$RUN/update.lock"
    if command -v flock >/dev/null 2>&1 && ! flock -n 9; then
        return 0  # an update is already running
    fi
    if [ -f "$RUN/update-request" ]; then
        rm -f "$RUN/update-request"
        update || true
        return 0
    fi
    local last=0
    [ -f "$RUN/update.json" ] && last="$(date -r "$RUN/update.json" +%s)"
    if [ $(( $(date +%s) - last )) -ge "$CHECK_EVERY" ]; then
        check >/dev/null || true
        if [ "${1:-}" = "--auto" ] && [ "$(waiting)" -gt 0 ]; then
            update || true
        fi
    fi
}

waiting() {  # changes waiting, from the last check
    grep -o '"behind": [0-9]*' "$RUN/update.json" 2>/dev/null | grep -o '[0-9]*$' || echo 0
}

install_cron() {
    local mode="--cron${1:+ $1}"
    local line="* * * * * cd $(pwd) && ./update.sh $mode >> run/update.log 2>&1"
    # one line only: an earlier one (with or without --auto) is replaced
    (crontab -l 2>/dev/null | grep -Fv "./update.sh --cron"; echo "$line") | crontab -
    echo "Installé : $line"
}

case "${1:-}" in
    --check) check ;;
    --cron) cron "${2:-}" ;;
    --install-cron) install_cron "${2:-}" ;;
    "") update ;;
    *) echo "Usage: $0 [--check | --cron [--auto] | --install-cron [--auto]]" >&2; exit 2 ;;
esac
