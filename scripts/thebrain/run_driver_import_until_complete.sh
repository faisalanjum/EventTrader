#!/bin/bash
set -u

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

attempt=1
while [ "$attempt" -le 20 ]; do
    echo "Driver import attempt $attempt/20"
    venv/bin/python scripts/thebrain/import_driver_set.py "$@"
    status=$?
    if [ "$status" -eq 0 ]; then
        exit 0
    fi
    echo "Driver import paused with status $status; retrying from the saved manifest in 5 seconds."
    sleep 5
    attempt=$((attempt + 1))
done

echo "Driver import did not finish after 20 resumable attempts." >&2
exit 1
