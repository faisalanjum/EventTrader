#!/usr/bin/env bash
set -uo pipefail

ROOT="${ROOT:-/home/faisal/EventMarketDB}"
INTERVAL_SEC="${INTERVAL_SEC:-60}"
LOG="${LOG:-/tmp/guidance_run_monitor.log}"
TASK_DIR="${TASK_DIR:-/tmp/claude-1000/-home-faisal-EventMarketDB/tasks}"

log() {
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG"
}

summarize_json() {
    local file="$1"
    python3 - "$file" <<'PY'
import json
import os
import sys

path = sys.argv[1]
try:
    with open(path) as fh:
        data = json.load(fh)
except Exception as exc:
    print(f"json_error={type(exc).__name__}:{exc}")
    raise SystemExit(0)

items = None
if isinstance(data, list):
    items = data
elif isinstance(data, dict):
    if isinstance(data.get("items"), list):
        items = data["items"]
    elif isinstance(data.get("guidance_items"), list):
        items = data["guidance_items"]
    elif isinstance(data.get("results"), list):
        items = data["results"]

if items is None:
    print(f"type={type(data).__name__} keys={','.join(sorted(data.keys())[:8]) if isinstance(data, dict) else '-'}")
else:
    labels = []
    for item in items[:5]:
        if isinstance(item, dict):
            label = item.get("label") or item.get("guidance_update_id") or "?"
            labels.append(str(label))
    print(f"items={len(items)} sample={'; '.join(labels) if labels else '-'}")
PY
}

snapshot_once() {
    log "--- snapshot begin ---"

    local pids
    pids="$(ps -ef | rg 'claude|trigger-extract|extraction_worker|guidance_write|warmup_cache' | rg -v 'rg ' || true)"
    if [[ -n "$pids" ]]; then
        while IFS= read -r line; do
            log "proc $line"
        done <<< "$pids"
    else
        log "proc none"
    fi

    if [[ -d "$TASK_DIR" ]]; then
        while IFS= read -r line; do
            log "task_file $line"
        done < <(find "$TASK_DIR" -maxdepth 1 -type f -printf '%TY-%Tm-%TdT%TH:%TM:%TSZ %f %s bytes\n' | sort -r | head -n 10)
    else
        log "task_dir missing path=$TASK_DIR"
    fi

    while IFS= read -r file; do
        [[ -f "$file" ]] || continue
        log "artifact $(stat -c '%y %n %s bytes' "$file" 2>/dev/null || echo "$file stat_error")"
        log "artifact_summary $(basename "$file") $(summarize_json "$file" 2>/dev/null || echo 'summary_error')"
    done < <(find /tmp -maxdepth 1 -type f \( -name 'gu_*.json' -o -name 'extract_pass_guidance_*.json' -o -name 'transcript_content_*.json' \) -printf '%T@ %p\n' | sort -nr | head -n 12 | awk '{print $2}')

    if [[ -f /tmp/guidance_issues_found.log ]]; then
        while IFS= read -r line; do
            log "issue $line"
        done < <(tail -n 20 /tmp/guidance_issues_found.log)
    fi

    log "reminder report latest monitor snapshot to user"
    log "--- snapshot end ---"
}

echo "=== guidance monitor started pid=$$ interval=${INTERVAL_SEC}s ===" > "$LOG"
while true; do
    snapshot_once || log "snapshot_error unexpected_nonzero_exit"
    sleep "$INTERVAL_SEC"
done
