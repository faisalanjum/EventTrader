#!/bin/bash
# Auto-resume driver. The LAN path resets client connections at ~320s during
# long cold prefills, but the SERVER completes and caches the work (verified:
# "200 in 5m19s" while the client saw ECONNRESET). So each resume lands on a
# warm cache and converges fast. The harness guarantees completed answers are
# never re-asked, so this is transport retry, not semantic repair.
C=/tmp/qwen38_bench/EventMarketDB/.claude/plans/Drivers/FinalDesign/QwenTests/table_evidence/choice_v2
PY=/home/faisal/EventMarketDB/venv/bin/python
cd "$C" || exit 1
for attempt in $(seq 1 40); do
  rows=$(wc -l < results/raw_results.jsonl 2>/dev/null || echo 0)
  ok=$($PY - <<'PY'
import json
try:
    rows=[json.loads(l) for l in open('results/raw_results.jsonl')]
    print(sum(1 for r in rows if r.get('ok')))
except Exception:
    print(0)
PY
)
  echo "attempt $attempt: rows=$rows ok=$ok"
  if [ "$ok" -ge 93 ]; then echo "ALL 93 COMPLETE"; break; fi
  LOCAL_LLM_MODEL=qwen3.8:27b-mlx LOCAL_LLM_NUM_CTX=16384 $PY choice_v2.py run >> /tmp/cv2_auto.log 2>&1
  sleep 3
done
echo "FINAL rows=$(wc -l < results/raw_results.jsonl)"
