#!/bin/sh
# Container entrypoint: wait for the database, apply migrations, then
# run the given command. Set RUN_MIGRATIONS=false to skip migrations
# (used by the worker so only one process migrates at a time).
set -e

python - <<'PY'
import os, re, socket, time

url = os.environ.get("DATABASE_URL", "")
match = re.search(r"@([^/:]+):(\d+)", url)
host, port = (match.group(1), int(match.group(2))) if match else ("db", 5432)
print(f"Waiting for database at {host}:{port} ...")
for _ in range(60):
    try:
        socket.create_connection((host, port), timeout=2).close()
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("Database not reachable")
print("Database is up.")
PY

# Ensure the upload spool directory exists (large import uploads).
# Never fatal: if the volume is not writable, fall back to the default
# temp dir so the API still starts (a crash here would block login too).
if [ -n "${TMPDIR:-}" ]; then
    if ! mkdir -p "$TMPDIR" 2>/dev/null; then
        echo "warn: cannot create TMPDIR=$TMPDIR; using default temp dir"
        unset TMPDIR
    fi
fi

if [ "${RUN_MIGRATIONS:-true}" != "false" ]; then
    echo "Applying migrations ..."
    alembic upgrade head
fi

exec "$@"
