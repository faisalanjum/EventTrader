#!/bin/bash
# The final G2/G3 writer, once, in the fresh private bench (Codex SEQ 1722 item 3).
set -u -o pipefail
P=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626
U=$P/budget_inputs_1720
L=$P/out/a4_final_lock_1683/launcher
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$U/logs" "$U/out_g23"
LOG="$U/logs/g23_$(date +%Y%m%dT%H%M%S).log"
# the writer EDITS its own module, and the bench is writable, so every attempt
# starts from the recovered source bytes again rather than from what the last
# attempt left behind (Codex SEQ 1722 item 3)
"$PY" -B "$U/seed_bench_g23.py" > "$U/logs/seed_g23.log" 2>&1 || exit 8
"$PY" -B "$U/build_g23_map.py" >/dev/null || exit 9
G1_UNIT="$U" KEEP_DIR="$U/out_g23" GEN_DIR=generators_g23 \
  timeout "${T:-3000}" "$PY" -B "$L/boundary.py" --host "$L/budget_g23_map.tsv" \
  "$U/replay_g1_1720.py" > "$LOG" 2>&1
rc=$?
echo "rc=$rc"; echo "log: $LOG"
grep -E "^(ok  |BAD |kept|PRESERVED|REFUSED|not produced)" "$LOG" | head -20
[ "$rc" -ne 0 ] && tail -14 "$LOG"
exit $rc
