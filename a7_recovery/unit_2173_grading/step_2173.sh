#!/bin/bash
# Advance ONE root by one segment. Never advances past a nonzero raw exit.
#   step_2173.sh KIND SEG RUN_ID RECEIPT  -> preserve+ingest the return, then publish next
#   step_2173.sh KIND -                   -> publish next only (nothing pending to ingest)
# The 2161 driver, with its command template replaced by the 2173 builder so a
# missed binding refuses instead of leaving an old path in the command.
set -euo pipefail
KIND="$1"
A7=/home/faisal/EventMarketDB-driver-recovery/a7_recovery
U="$A7/unit_2173_grading"; L="$A7/unit_1947/logs"; K="${KIND,,}"
PY=/home/faisal/EventMarketDB/venv/bin/python3
OP=../../unit_2020_codex_check/run_grading_2086.py
cd /home/faisal/EventMarketDB-driver-recovery

run_op () {  # $1=command $2=tag $3=segment $4=receipt $5=run_id ; REFUSES on raw exit != 0
  local cmd="$1" tag="$2" seg="$3" rec="$4" run="$5"
  $PY -B "$U/build_command_2173.py" "$tag" "$OP" "$KIND" \
      "A7_GRADING_COMMAND=$cmd" "A7_GRADING_SEGMENT=$seg" \
      "A7_GRADING_RECEIPT_SHA256=$rec" "A7_GRADING_WORKFLOW_RUN=$run" >/dev/null
  bash "$U/commands/cmd_$tag.sh" >/dev/null 2>&1 || true   # the wrapper's status is not the job's
  local raw; raw=$(cat "$L/attempt_$tag/exit")
  echo "$cmd raw exit $raw"
  if [ "$raw" != "0" ]; then
    echo "REFUSING TO ADVANCE: $cmd raw exit $raw"; tail -c 600 "$L/attempt_$tag/stderr.txt"; exit 9
  fi
}

if [ "$2" != "-" ]; then
  SEG="$2"; RUN_ID="$3"; RECEIPT="$4"; SS=$(printf '%02d' "$SEG")
  REC=$($PY -B "$U/preserve_run_2173.py" "$KIND" "$SEG" "$RUN_ID")
  echo "PRESERVED $REC"
  echo "$REC" >> "$U/COLLECTION_LEDGER_2173.jsonl"
  run_op ingest "core_ingest2173_${K}_$SS" "$SEG" "$RECEIPT" "$RUN_ID"
  # An INVALID reading is a lawful recorded outcome under the existing
  # invalid-only path, not an operator failure: it is reported and carried,
  # never silently passed. Only a nonzero raw exit stops this root.
  $PY -B -c "
import io,json
d=json.load(io.open('$U/$KIND/run/finalization.seg$SS.json'))
print('LEDGER', json.dumps(d['ledger'],sort_keys=True), 'PROBLEMS', json.dumps(d['problems']))" \
    | tee -a "$U/COLLECTION_LEDGER_2173.jsonl"
  LAST="$SEG"
else
  LAST=$($PY -B -c "
import os
run='$U/$KIND/run'
print(max(int(f.split('.seg')[1].split('.')[0]) for f in os.listdir(run) if f.startswith('receipt.seg')))")
fi

run_op prepare "core_prep2173_${K}_$(printf '%02d' $((LAST+1)))" "$LAST" "0" "-"
NEXT=$($PY -B -c "
import os
run='$U/$KIND/run'
print(max(int(f.split('.seg')[1].split('.')[0]) for f in os.listdir(run) if f.startswith('receipt.seg')))")
if [ "$NEXT" -le "$LAST" ]; then echo "NO_NEXT_SEGMENT last=$LAST"; exit 0; fi
$PY -B "$U/materialize_segment_2173.py" "$KIND" "$NEXT" | tr -d '\n' | sed 's/  */ /g'; echo
$PY -B -c "
import json,io,hashlib
run='$U/$KIND/run'; n=$NEXT
inv=json.load(io.open(run+'/invocation.seg%02d.json'%n))
print('NEXT_SEGMENT', n)
print('NEXT_RECEIPT', hashlib.sha256(io.open(run+'/receipt.seg%02d.json'%n,'rb').read()).hexdigest())
print('NEXT_SCRIPT', inv['scriptPath'])
print('NEXT_ARGS', json.dumps(inv['args']))"
