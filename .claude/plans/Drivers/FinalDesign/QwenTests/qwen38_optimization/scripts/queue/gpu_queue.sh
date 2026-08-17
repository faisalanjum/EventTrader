#!/bin/bash
# Battery-gated GPU job queue for the MacBook on a 30W adapter.
# Runs jobs sequentially; each job is resumable. A job runs only while battery
# >= START_MIN at launch and is killed (and later resumed) if battery <= STOP_MIN.
SCR=/private/tmp/claude-501/-Users-faanjum-Developer/4babfc37-ad53-4444-b458-a7efadb4d7eb/scratchpad
LOG=$SCR/gpu_queue.log
STATE=$SCR/gpu_queue.state
START_MIN=${START_MIN:-35}
STOP_MIN=${STOP_MIN:-12}
REMOTE=faisal@192.168.40.73
SSH="ssh -o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4"
T=/tmp/qwen38_bench/EventMarketDB/.claude/plans/Drivers/FinalDesign/QwenTests/table_evidence

log(){ echo "$(date '+%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
batt(){ pmset -g batt | grep -o '[0-9]*%' | head -1 | tr -d '%'; }
charging(){ pmset -g batt | grep -q "charging" && echo yes || echo no; }

remote_kill(){
  $SSH $REMOTE 'pkill -f "choice_v2[.]py run" ; pkill -f "run_until_don[e].sh"; true' 2>/dev/null
}

wait_for_battery(){ # $1 = threshold
  while true; do
    b=$(batt)
    if [ "$b" -ge "$1" ]; then return; fi
    echo "waiting batt=$b% (need $1%) charging=$(charging)" > "$STATE"
    sleep 60
  done
}

# run_job NAME CMD  -- CMD is a bash -c string; must be resumable
run_job(){
  name="$1"; cmd="$2"
  while true; do
    wait_for_battery "$START_MIN"
    log "JOB $name START batt=$(batt)%"
    echo "running $name" > "$STATE"
    bash -c "$cmd" >> "$LOG.$name" 2>&1 &
    pid=$!
    while kill -0 $pid 2>/dev/null; do
      b=$(batt)
      if [ "$b" -le "$STOP_MIN" ]; then
        log "JOB $name PAUSE batt=$b% -> killing"
        remote_kill; kill $pid 2>/dev/null; sleep 2; kill -9 $pid 2>/dev/null
        wait $pid 2>/dev/null
        pid=""
        break
      fi
      sleep 20
    done
    if [ -n "$pid" ]; then
      wait $pid; rc=$?
      log "JOB $name EXIT rc=$rc batt=$(batt)%"
      if [ $rc -eq 0 ]; then return 0; fi
      log "JOB $name FAILED rc=$rc -> stopping queue"; echo "failed $name" > "$STATE"; return 1
    fi
    log "JOB $name will resume at >= ${START_MIN}%"
  done
}

log "QUEUE START batt=$(batt)% START_MIN=$START_MIN STOP_MIN=$STOP_MIN"

# J1: primed full choice_v2 (dense) - cold trie (model was reloaded at 21:16)
run_job cv2_primed "$SSH $REMOTE 'bash /tmp/qwen38_scratch/s2/run_until_done.sh $T/choice_v2 /tmp/qwen38_scratch/s2/cv2_primed.log'" || exit 1

# J2: immediate warm re-run (cache persistence across runs). Keep J1 results.
run_job cv2_primed_rerun "$SSH $REMOTE 'cd $T/choice_v2 && { [ -d results_primed_run1 ] || mv results results_primed_run1; } && bash /tmp/qwen38_scratch/s2/run_until_done.sh $T/choice_v2 /tmp/qwen38_scratch/s2/cv2_primed_rerun.log && { [ -d results_primed_run2_warm ] || mv results results_primed_run2_warm; }'" || exit 1

# J4: num_ctx cost (reloads the model twice; drops the trie - fine here)
run_job ctx_cost "python3 $SCR/ctx_cost.py" || exit 1

# J3: compact-encoding full run (new prompts -> cold; priming on)
run_job cv2_compact "$SSH $REMOTE 'bash /tmp/qwen38_scratch/s2/run_until_done.sh $T/choice_v2_compact /tmp/qwen38_scratch/s2/cv2_compact.log'" || exit 1

# J5: restore production state: model resident at num_ctx 16384
run_job restore "curl -s localhost:11434/api/chat -d '{\"model\":\"qwen3.8:27b-mlx\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: OK\"}],\"stream\":false,\"think\":false,\"options\":{\"num_ctx\":16384,\"temperature\":0,\"num_predict\":4}}' > /dev/null" || exit 1

log "QUEUE DONE batt=$(batt)%"
echo "done" > "$STATE"
