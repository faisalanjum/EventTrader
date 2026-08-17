#!/bin/bash
SCR=/private/tmp/claude-501/-Users-faanjum-Developer/4babfc37-ad53-4444-b458-a7efadb4d7eb/scratchpad
LOG=$SCR/gpu_queue2.log; STATE=$SCR/gpu_queue2.state
START_MIN=${START_MIN:-30}; STOP_MIN=${STOP_MIN:-12}
REMOTE=faisal@192.168.40.73
SSH="ssh -o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4"
T=/tmp/qwen38_bench/EventMarketDB/.claude/plans/Drivers/FinalDesign/QwenTests/table_evidence
PY=/home/faisal/EventMarketDB/venv/bin/python
log(){ echo "$(date '+%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
batt(){ pmset -g batt | grep -o '[0-9]*%' | head -1 | tr -d '%'; }
remote_kill(){ $SSH $REMOTE 'pkill -f "qf01[.]py run"; pkill -f "choice_v2[.]py run"; pkill -f "run_until_don[e].sh"; true' 2>/dev/null; }
wait_for_battery(){ while true; do b=$(batt); if [ "$b" -ge "$1" ]; then return; fi; echo "waiting batt=$b% (need $1%)" > "$STATE"; sleep 60; done; }
run_job(){ name="$1"; cmd="$2"
  while true; do wait_for_battery "$START_MIN"; log "JOB $name START batt=$(batt)%"; echo "running $name" > "$STATE"
    bash -c "$cmd" >> "$LOG.$name" 2>&1 & pid=$!
    while kill -0 $pid 2>/dev/null; do b=$(batt); if [ "$b" -le "$STOP_MIN" ]; then log "JOB $name PAUSE batt=$b%"; remote_kill; kill $pid 2>/dev/null; sleep 2; kill -9 $pid 2>/dev/null; wait $pid 2>/dev/null; pid=""; break; fi; sleep 20; done
    if [ -n "$pid" ]; then wait $pid; rc=$?; log "JOB $name EXIT rc=$rc batt=$(batt)%"; [ $rc -eq 0 ] && return 0; log "JOB $name FAILED rc=$rc"; echo "failed $name" > "$STATE"; return 1; fi
    log "JOB $name will resume at >= ${START_MIN}%"; done; }
# wait for queue 1 to finish
until grep -q "QUEUE DONE" $SCR/gpu_queue.log 2>/dev/null; do echo "waiting for queue1" > "$STATE"; sleep 60; done
log "QUEUE2 START batt=$(batt)%"
# J8: dense choice_v2 with TABLE-level priming (cold trie after J3/J4) - expect ~6 min
run_job cv2_tableprime "$SSH $REMOTE 'bash /tmp/qwen38_scratch/s2/run_until_done.sh $T/choice_v2 /tmp/qwen38_scratch/s2/cv2_tableprime.log && cd $T/choice_v2 && LOCAL_LLM_MODEL=qwen3.8:27b-mlx LOCAL_LLM_NUM_CTX=16384 $PY choice_v2.py score > /tmp/qwen38_scratch/s2/cv2_tableprime_score.out 2>&1'" || exit 1

# J6: qf01 aligned, table-first + priming (19 calls, resumable? no - qf01 refuses partial; so remove partial results on retry)
run_job qf01_primed "$SSH $REMOTE 'cd $T && { [ ! -f results/raw_results.jsonl ] || [ -f results/run_record.json ] || rm -rf results; } && LOCAL_LLM_MODEL=qwen3.8:27b-mlx LOCAL_LLM_NUM_CTX=16384 $PY qf01.py run && LOCAL_LLM_MODEL=qwen3.8:27b-mlx LOCAL_LLM_NUM_CTX=16384 $PY qf01.py score > /tmp/qwen38_scratch/s2/qf01_score.out 2>&1'" || exit 1
# J7: reader-style decode probe (2 runs)
run_job decode_probe "python3 $SCR/decode_probe.py && python3 $SCR/decode_probe.py" || exit 1
log "QUEUE2 DONE batt=$(batt)%"; echo "done" > "$STATE"
