#!/bin/bash
# ONE segment step for one kind: preserve the returned evidence, ingest it
# through the existing operator, then publish+materialize the next segment.
# Boundary commands are run one at a time by the caller; this does not launch
# any model call and never rewrites a receipt.
set -euo pipefail
KIND="$1"; SEGMENT="$2"; RUN_ID="$3"; RECEIPT="$4"
A7=/home/faisal/EventMarketDB-driver-recovery/a7_recovery
U=$A7/unit_2161_execution
cd /home/faisal/EventMarketDB-driver-recovery
TAG="core_ing2161_${KIND,,}_$(printf '%02d' "$SEGMENT")"
sed -e "s|A7_GRADING_COMMAND='[a-z]*'|A7_GRADING_COMMAND='ingest'|" \
    -e "s|A7_GRADING_SEGMENT='[0-9]*'|A7_GRADING_SEGMENT='$SEGMENT'|" \
    -e "s|A7_GRADING_RECEIPT_SHA256='[a-f0-9]*'|A7_GRADING_RECEIPT_SHA256='$RECEIPT'|" \
    -e "s|core_op2161_${KIND,,}_status|$TAG|g" \
    "$U/commands/cmd_core_op2161_${KIND,,}_status.sh" > "$U/commands/cmd_$TAG.sh"
grep -q "A7_GRADING_WORKFLOW_RUN" "$U/commands/cmd_$TAG.sh" \
  || sed -i "s|A7_GRADING_COMMAND=|A7_GRADING_WORKFLOW_RUN='$RUN_ID' A7_GRADING_COMMAND=|" "$U/commands/cmd_$TAG.sh"
sed -i "s|A7_GRADING_WORKFLOW_RUN='[^']*'|A7_GRADING_WORKFLOW_RUN='$RUN_ID'|" "$U/commands/cmd_$TAG.sh"
bash "$U/commands/cmd_$TAG.sh" >/dev/null 2>&1 || true
echo "ingest raw exit $(cat $A7/unit_1947/logs/attempt_$TAG/exit)"
tail -c 400 "$A7/unit_1947/logs/attempt_$TAG/stdout.txt"
echo "--- stderr ---"; tail -c 300 "$A7/unit_1947/logs/attempt_$TAG/stderr.txt"
