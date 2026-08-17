#!/bin/bash
# battery-gated resumable runner: rerun until ALL DONE; pause (rc 75) waits for >=30%
cd "$(dirname "$0")"
LOG=identity_exam.log
batt(){ pmset -g batt | grep -o '[0-9]*%' | head -1 | tr -d '%'; }
for attempt in $(seq 1 30); do
  while [ "$(batt)" -lt 30 ] && [ $attempt -gt 1 ]; do echo "$(date '+%H:%M') waiting batt=$(batt)%" >> $LOG; sleep 60; done
  echo "$(date '+%H:%M') attempt $attempt batt=$(batt)%" >> $LOG
  python3 identity_exam.py run --model qwen3.8:27b-mtp-q4_K_M --max-tokens 600 --stop-batt 12 >> $LOG 2>&1
  rc=$?
  if grep -q "ALL DONE" $LOG; then echo "$(date '+%H:%M') COMPLETE" >> $LOG; break; fi
  echo "$(date '+%H:%M') rc=$rc" >> $LOG; sleep 5
done
python3 identity_exam.py score --model qwen3.8:27b-mtp-q4_K_M >> $LOG 2>&1
# restore production model (MLX) resident at 16384
curl -s localhost:11434/api/chat -d '{"model":"qwen3.8:27b-mlx","messages":[{"role":"user","content":"Reply with exactly: OK"}],"stream":false,"think":false,"options":{"num_ctx":16384,"temperature":0,"num_predict":4}}' > /dev/null
echo "$(date '+%H:%M') production model restored" >> $LOG
