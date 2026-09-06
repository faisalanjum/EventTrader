#!/bin/bash
# Fail-forward loop for the one demanded historical run (Codex SEQ 1698).
#
# Run the reconstruction; when it stops because an ERA OWNER asked for a bench
# file the projection does not carry, place exactly that path through the one
# placer - which accepts only a canonical pin or a unanimous durable byte and
# otherwise refuses - rebuild the maps, and run again. Any other failure, or a
# placement the placer refuses, ends the loop with the evidence intact.
set -u -o pipefail
R=/home/faisal/EventMarketDB-driver-recovery
P=$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626
UNIT=$P/out/a4_final_lock_1683
L=$UNIT/launcher
PY=/home/faisal/EventMarketDB/venv/bin/python3
BENCH_LOGICAL=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/
LOG=$UNIT/tests/era_v3_1479.log
export PYTHONDONTWRITEBYTECODE=1

for i in $(seq 1 "${MAX_ITERS:-15}"); do
  "$PY" -B "$UNIT/tests/build_map.py" >/dev/null || exit 9
  "$PY" -B "$UNIT/tests/build_era_map.py" "$UNIT/era_owners/v3_1479" v3_1479_map.tsv >/dev/null || exit 9
  V3_PINS="$P/pins_1636.json" V3_TSV="$P/inputs/history_store/WORKFLOWS.tsv" \
    V3_LABEL=v3_1479 KEEP_DIR="$UNIT/runs" \
    timeout 900 "$PY" -B "$L/boundary.py" --host "$L/v3_1479_map.tsv" "$L/era_v3_1479.py" \
    > "$LOG" 2>&1
  rc=$?
  echo "--- iteration $i rc=$rc"
  [ "$rc" -eq 0 ] && { tail -6 "$LOG"; exit 0; }

  miss=$(grep -o "FileNotFoundError:.*'${BENCH_LOGICAL}[^']*'" "$LOG" | tail -1 |
         sed "s#.*'${BENCH_LOGICAL}##; s#'\$##")
  if [ -z "$miss" ]; then
    tail -25 "$LOG"; echo "STOP: not a missing bench file"; exit 1
  fi
  echo "missing bench file: $miss"
  "$PY" -B "$UNIT/tests/place_missing.py" "$miss" | grep -E 'unanimous|^   \+|candidate genuine|NOT PINNED' || true
  if ! [ -f "$UNIT/bench/bench_1306/$miss" ]; then
    echo "STOP: the placer refused $miss"; exit 2
  fi
done
echo "STOP: iteration cap reached"; exit 3
