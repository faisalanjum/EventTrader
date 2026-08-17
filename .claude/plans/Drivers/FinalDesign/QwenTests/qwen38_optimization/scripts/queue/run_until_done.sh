#!/bin/bash
# Remote (Minisforum) driver: loop `choice_v2.py run` in DIR until 93 ok answers.
# Transport retry only - the harness never re-asks a completed answer.
# Usage: run_until_done.sh <harness_dir> <log_file>
DIR="$1"; LOGF="$2"
PY=/home/faisal/EventMarketDB/venv/bin/python
cd "$DIR" || exit 1
for attempt in $(seq 1 60); do
  ok=$($PY - <<'PY'
import json
try:
    rows=[json.loads(l) for l in open('results/raw_results.jsonl')]
    print(sum(1 for r in rows if r.get('ok')))
except Exception:
    print(0)
PY
)
  echo "$(date +%H:%M:%S) attempt $attempt ok=$ok" | tee -a "$LOGF"
  if [ "$ok" -ge 93 ]; then echo "ALL 93 COMPLETE" | tee -a "$LOGF"; exit 0; fi
  if [ -f results/run_record.json ]; then echo "run_record exists but ok<93 -> stop" | tee -a "$LOGF"; exit 2; fi
  LOCAL_LLM_MODEL=qwen3.8:27b-mlx LOCAL_LLM_NUM_CTX=16384 $PY choice_v2.py run >> "$LOGF" 2>&1
  sleep 3
done
exit 3
