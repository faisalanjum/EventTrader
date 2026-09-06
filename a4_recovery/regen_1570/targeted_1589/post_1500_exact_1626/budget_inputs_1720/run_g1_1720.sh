#!/bin/bash
# One gated replay of the recorded G1 chain inside the private boundary.
set -u -o pipefail
P=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626
U=$P/budget_inputs_1720
L=$P/out/a4_final_lock_1683/launcher
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1
# evidence is never overwritten: each attempt gets its own log (Codex SEQ 1722)
mkdir -p "$U/logs"
LOG="$U/logs/replay_$(date +%Y%m%dT%H%M%S).log"
"$PY" -B "$U/build_budget_map.py" >/dev/null || exit 9
mkdir -p "$U/out_g1"
G1_UNIT="$U" KEEP_DIR="$U/out_g1" STOP_AFTER="${STOP_AFTER:-64992_run4_root}" \
  timeout "${T:-1800}" "$PY" -B "$L/boundary.py" --host "$L/budget_g1_map.tsv" \
  "$U/replay_g1_1720.py" > "$LOG" 2>&1
rc=$?
echo "rc=$rc"
grep -E "^(ok  |BAD |kept|PRESERVED|REFUSED)" "$LOG" | head -20
[ "$rc" -ne 0 ] && tail -12 "$LOG"
echo "log: $LOG"
exit $rc
