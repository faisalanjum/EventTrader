#!/bin/bash
# One A4 pipeline run inside the existing no-write boundary (Codex SEQ 1725).
set -u -o pipefail
P=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626
UNIT=$P/out/a4_final_lock_1683
L=$UNIT/launcher
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$UNIT/logs" "$UNIT/out"
LOG="$UNIT/logs/a4_$(date +%Y%m%dT%H%M%S).log"
A4_A6="${A4_A6:-}" "$PY" -B "$UNIT/tests/build_1501_map.py" >/dev/null || exit 9
A4_STEPS="${A4_STEPS:-}" A4_ROUND="${A4_ROUND:-1}" A4_LEDGER="${A4_LEDGER:-}" KEEP_DIR="$UNIT/out" \
  timeout "${T:-3000}" "$PY" -B "$L/boundary.py" --host "$L/a4_final_map.tsv" \
  "$UNIT/tests/a4_pipeline.py" > "$LOG" 2>&1
rc=$?
echo "rc=$rc"; echo "log: $LOG"
grep -E "^(ok  |BAD |kept|PRESERVED|REFUSED)" "$LOG" | head -30
[ "$rc" -ne 0 ] && tail -16 "$LOG"
exit $rc
