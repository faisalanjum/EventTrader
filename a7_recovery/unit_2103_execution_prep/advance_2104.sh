#!/bin/bash
# One segment's whole post-call sequence, then set up the next call.
#
#   advance_2104.sh <kind> <segment just called> <workflow id>
#
# preserve -> ingest -> (prepare next | retry the invalid lanes) -> materialize
# -> preflight -> launch note -> print the exact scriptPath and args to call.
#
# The original finalizer owns retry eligibility; the pinned G2 format filter
# removes successfully recovered replies from that list. The published
# invocation supplies args verbatim. Any non-zero payload exit stops the chain.
set -euo pipefail
KIND="$1"; SEG="$2"; WF="$3"
case "$KIND" in G2|G3) ;; *) echo "STOP: expected G2 or G3" >&2; exit 1 ;; esac
if [ "$KIND" = "G2" ]; then
  : "${A7_RETRY_PLAN_SHA256:?approved retry-filter hash required}"
  : "${A7_FORMAT_CODE_SHA256:?approved format-code hash required}"
  : "${A7_FORMAT_RULE_SHA256:?approved format-rule hash required}"
fi
REC=/home/faisal/EventMarketDB-driver-recovery
A7=$REC/a7_recovery
U=$A7/unit_2103_execution_prep
UNIT=$A7/unit_2103_g23_grading/$KIND
LAUNCH=$UNIT/LAUNCH.json
LSHA=$(sha256sum $LAUNCH | cut -d' ' -f1)
TAG=$(printf 'seg%02d' $SEG)
STAMP=$(date +%H%M%S)

run() {   # run() <command> <tag> [extra env assignments...]
  local cmd="$1"; local tag="$2"; shift 2
  local payload=run_grading_2086.py
  if [ "$cmd" = "retry_plan" ]; then
    payload=meaning_retry_plan_2107.py
    cmd=preflight
  fi
  cd $REC
  env PYTHONDONTWRITEBYTECODE=1 \
    A7_RUN_BINDING=$A7/unit_2020_codex_check/map_g23_transport_2103.tsv \
    A7_LANE_INPUT_PROFILES=/tmp/a7_lane_input_profiles.json \
    A7_SOURCE_PROJECTS=/home/faisal/.claude/projects \
    A7_REVIEW_OUT=/tmp/a7_real_package_1947 \
    A7_SOURCE_CONTEXT=/tmp/a7_source_context \
    A7_GRADING_LAUNCH=$LAUNCH A7_GRADING_LAUNCH_SHA256=$LSHA \
    A7_GRADING_COMMAND=$cmd "$@" \
    bash a7_recovery/unit_1947/ledger/run_real_1947.sh \
      ../unit_2020_codex_check/map_g23_transport_2103.tsv \
      "../../unit_2020_codex_check/$payload" "$tag" 240 >/dev/null 2>&1 || true
  local log=$A7/unit_1947/logs/attempt_$tag
  local code; code=$(cat $log/exit 2>/dev/null || echo 99)
  echo "  $cmd exit=$code stderr=$(stat -c%s $log/stderr.txt 2>/dev/null || echo ?)B" >&2
  if [ "$code" != "0" ]; then
    echo "STOP: $cmd exited $code; see $log" >&2
    sed -n '1,25p' $log/stdout.txt >&2 2>/dev/null || true
    sed -n '1,15p' $log/stderr.txt >&2 2>/dev/null || true
    exit 1
  fi
  echo "$log"
}

# Codex step 4: the returned workflow id is recorded immediately. Idempotent -
# a note that already names this workflow is left alone, so re-running is safe.
PYTHONDONTWRITEBYTECODE=1 python3 -B $U/record_workflow_2104.py "$KIND" "$SEG" "$WF" >&2

echo "== preserve $KIND $TAG $WF" >&2
PYTHONDONTWRITEBYTECODE=1 python3 -B $U/preserve_native_2104.py "$KIND" "$SEG" "$WF" >&2

echo "== ingest" >&2
RSHA=$(sha256sum $UNIT/run/receipt.$TAG.json | cut -d' ' -f1)
ING=$(run ingest "core2104_${KIND,,}i${SEG}_$STAMP" \
      A7_GRADING_SEGMENT=$SEG A7_GRADING_RECEIPT_SHA256=$RSHA A7_GRADING_WORKFLOW_RUN=$WF)
cat $ING/stdout.txt >&2

# the finalizer decides; this only reads it
RETRY_SOURCE="$UNIT/run/finalization.$TAG.json"
if [ "$KIND" = "G2" ]; then
  FILTER=$(run retry_plan "core2107_g2filter${SEG}_$STAMP" \
           A7_GRADING_SEGMENT=$SEG A7_GRADING_RECEIPT_SHA256=$RSHA)
  RETRY_SOURCE="$FILTER/stdout.txt"
fi
NEXT=$(PYTHONDONTWRITEBYTECODE=1 python3 -B - "$RETRY_SOURCE" "$KIND" <<'PY'
import json, io, sys
with io.open(sys.argv[1], encoding='utf-8') as fh:
    if sys.argv[2] == 'G2':
        records = [json.loads(line) for line in fh if line.startswith('{')]
        plans = [record for record in records if 'retry_lanes' in record]
        assert len(plans) == 1, 'expected exactly one verified retry plan'
        eligible = plans[0]['retry_lanes']
    else:
        d = json.load(fh)
        eligible = list(d.get('retry') or [])
        assert len(eligible) == d['ledger']['retry'], (
            'the finalizer counts %d retries but names %d: %s'
            % (d['ledger']['retry'], len(eligible), eligible))
print(('retry ' + ','.join(eligible)) if eligible else 'prepare')
PY
)
echo "== next: $NEXT" >&2

if [ "${NEXT%% *}" = "retry" ]; then
  LANES="${NEXT#retry }"
  # Codex SEQ 2105: never spend a retry on a defect G2 has already shown.
  if [ "$KIND" != "G2" ]; then
    DEFECT=$(PYTHONDONTWRITEBYTECODE=1 python3 -B $U/known_defect_2105.py "$UNIT/run/finalization.$TAG.json" | tail -1)
    if [ "$DEFECT" = "REPEATS_KNOWN_DEFECT" ]; then
      echo "STOP: this failure repeats the known G2 defect; retry NOT spent" >&2
      PYTHONDONTWRITEBYTECODE=1 python3 -B $U/known_defect_2105.py "$UNIT/run/finalization.$TAG.json" >&2
      echo "STOPPED_ON_KNOWN_DEFECT=1"
      exit 0
    fi
  fi
  OUT=$(run retry "core2104_${KIND,,}r${SEG}_$STAMP" A7_GRADING_RETRY_LANES="$LANES")
else
  LEFT=$(PYTHONDONTWRITEBYTECODE=1 python3 -B $U/rows_left_2104.py "$UNIT/run")
  if [ "$LEFT" = "0" ]; then
    echo "ALL_ROWS_ACCOUNTED=1  (no empty extra segment prepared)"
    exit 0
  fi
  OUT=$(run prepare "core2104_${KIND,,}p${SEG}_$STAMP")
fi
cat $OUT/stdout.txt >&2

NEWSEG=$(PYTHONDONTWRITEBYTECODE=1 python3 -B - "$OUT/stdout.txt" <<'PY'
import json, io, re, sys
text = io.open(sys.argv[1], encoding='utf-8').read()
for line in text.strip().split('\n'):
    line = line.strip()
    if line.startswith('{') and line.endswith('}'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if 'packet' in d:
            print(d['segment']); break
    hit = re.match(r'^SEGMENT\s*:\s*(\d+)\s*$', line)
    if hit:
        print(hit.group(1)); break
PY
)
[ -n "$NEWSEG" ] || { echo "STOP: could not read the new segment number" >&2; exit 1; }
echo "== new segment $NEWSEG" >&2

PYTHONDONTWRITEBYTECODE=1 python3 -B $U/materialize_segment_2104.py "$KIND" "$NEWSEG" >&2
NTAG=$(printf 'seg%02d' $NEWSEG)
NRSHA=$(sha256sum $UNIT/run/receipt.$NTAG.json | cut -d' ' -f1)
PRE=$(run preflight "core2104_${KIND,,}f${NEWSEG}_$STAMP" \
      A7_GRADING_SEGMENT=$NEWSEG A7_GRADING_RECEIPT_SHA256=$NRSHA)
PYTHONDONTWRITEBYTECODE=1 python3 -B $U/launch_note_2104.py "$KIND" "$NEWSEG" $PRE/stdout.txt >/dev/null

echo "NEXT_KIND=$KIND"
echo "NEXT_SEGMENT=$NEWSEG"
echo "NEXT_SCRIPT=$(PYTHONDONTWRITEBYTECODE=1 python3 -Bc "import json,io;print(json.load(io.open('$UNIT/run/invocation.$NTAG.json'))['scriptPath'])")"
echo "NEXT_ARGS=$(PYTHONDONTWRITEBYTECODE=1 python3 -Bc "import json,io;print(json.dumps(json.load(io.open('$UNIT/run/invocation.$NTAG.json'))['args'],separators=(',',':')))")"
