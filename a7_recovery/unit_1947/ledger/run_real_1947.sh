#!/bin/bash
# The REAL source-review binding. No TEST reply seed, no TEST event raw, no
# TEST projects override - run_1947.sh carried all three and is not a real
# run path (Codex SEQ 1948). Only the boundary, the map and the payload.
set -u
MAP="$1"; PAYLOAD="$2"; TAG="$3"; LIMIT="${4:-900}"
R=/home/faisal/EventMarketDB-driver-recovery
U=$R/a7_recovery/unit_1947
BND=$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher/boundary.py
PY=/home/faisal/EventMarketDB/venv/bin/python3
ATT="$U/logs/attempt_$TAG"
mkdir "$ATT" || { echo "REFUSE: $ATT exists - that attempt is evidence"; exit 5; }
cd "$R" || exit 2
setsid --wait timeout --signal=TERM --kill-after=20 "$LIMIT" \
  env PYTHONDONTWRITEBYTECODE=1 \
      A7_TAG="$TAG" \
      A7_ATTEMPT_DIR="/tmp/a7_logs_1781/attempt_$TAG" \
      A7_REVIEW_OUT="${A7_REVIEW_OUT:?the real packet destination is required}" \
      A7_SOURCE_CONTEXT="${A7_SOURCE_CONTEXT:?the issuer context is required}" \
      CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-128000}" \
      GIT_DIR="/home/faisal/EventMarketDB/.git" \
    "$PY" -B "$BND" --host "$U/$MAP" "$U/ledger/$PAYLOAD" \
    > "$ATT/stdout.txt" 2> "$ATT/stderr.txt" < /dev/null &
WRAP=$!
LEADER=""
for _ in 1 2 3 4 5; do LEADER=$(pgrep -P "$WRAP" | head -1); [ -n "$LEADER" ] && break; sleep 0.2; done
{ printf "attempt\t%s\npayload\t%s\nmap\t%s\nwrapper_pid\t%s\npayload_pid\t%s\nstarted_utc\t%s\nstate\trunning\n" \
    "$TAG" "$PAYLOAD" "$MAP" "$WRAP" "${LEADER:-}" "$(date -u +%FT%TZ)"; } > "$ATT/owner.tsv"
wait $WRAP; RC=$?
echo "$RC" > "$ATT/exit"
sed -i "s/^state\trunning$/state\tfinished exit $RC/" "$ATT/owner.tsv"
echo "raw exit $RC"
