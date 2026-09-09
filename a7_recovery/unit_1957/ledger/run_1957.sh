#!/bin/bash
# run_1957.sh <map> <payload> <tag> [limit]  - one owned attempt, real exit code.
# Same shape as run_aligned_1953.sh. Two differences:
#   * staged payload inputs go under logs/attempt_<tag>, which IS the rw mount
#     /tmp/a7_logs_1781 for this unit (1953's out_a/ path does not exist here);
#   * A7_LANE_INPUT_PROFILES names the SERVED approved lane-input artifact, the
#     same way A7_SOURCE_CONTEXT names the served issuer tree. The map pins that
#     row read-only at its approved sha, so the boundary verifies it on the host
#     before any namespace exists.
set -u
MAP="$1"; PAYLOAD="$2"; TAG="$3"; LIMIT="${4:-900}"
R=/home/faisal/EventMarketDB-driver-recovery
A=$R/a7_recovery
U=$A/unit_1957
S=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad
BND=$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher/boundary.py
PY=/home/faisal/EventMarketDB/venv/bin/python3
ATT="$U/logs/attempt_$TAG"
if grep -q "^/tmp/a7_logs_1781/attempt_$TAG	" "$U/$MAP"; then
  echo "REFUSE: the binding already serves /tmp/a7_logs_1781/attempt_$TAG"; exit 7
fi
mkdir "$ATT" || { echo "REFUSE: $ATT already exists - that attempt is evidence"; exit 5; }
mkdir -p "$ATT/src_replies"
cp "$A/unit_1893/logs/attempt_reh3/TEST_replies/$(ls -1 $A/unit_1893/logs/attempt_reh3/TEST_replies | head -1)" \
   "$ATT/event_valid.raw.json"
cp "${A7_FIXTURE_REPLIES:-$A/unit_1893/logs/attempt_reh3/TEST_replies}"/*.json "$ATT/src_replies/"
cd "$R" || exit 2
setsid --wait timeout --signal=TERM --kill-after=20 "$LIMIT" \
  env PYTHONDONTWRITEBYTECODE=1 \
      A7_TAG="$TAG" \
      A7_PHASE="${A7_PHASE:-after}" \
      A7_ATTEMPT_DIR="/tmp/a7_logs_1781/attempt_$TAG" \
      A7_LANE_INPUT_PROFILES="${A7_LANE_INPUT_PROFILES:-/tmp/a7_lane_input_profiles.json}" \
      A7_SIGN_RAW="$S/lock/candidate/final_sign.attempt1.raw.json" \
      A7_TEST_REPLIES="/tmp/a7_logs_1781/attempt_$TAG/src_replies" \
      A7_EVENT_RAW="/tmp/a7_logs_1781/attempt_$TAG/event_valid.raw.json" \
      A7_REVIEW_OUT="${A7_REVIEW_OUT:-$A/unit_1895/logs/inventory_review}" \
      A7_RUN_BINDING="$U/$MAP" \
      A7_LOCK_OWNERS="${A7_LOCK_OWNERS:-$U/lock_owners}" \
      A7_KEY_PATH="${A7_KEY_PATH:-owed}" \
      A7_LIFECYCLE_ROOT="${A7_LIFECYCLE_ROOT:-/tmp/a7_logs_1781/lifecycle}" \
      A7_PRISTINE_PACKET="${A7_PRISTINE_PACKET:-}" \
      A7_COMPLETED_PACKET="${A7_COMPLETED_PACKET:-}" \
      A7_BEFORE_FINAL="${A7_BEFORE_FINAL:-$A/unit_1953/ledger/build_kfields_final.BEFORE_t5.py}" \
      A7_AUTHORITY="${A7_AUTHORITY:-/home/faisal/.core827-orchestrator/archive_CODEX_1957.md}" \
      A7_SOURCE_CONTEXT="${A7_SOURCE_CONTEXT:-/tmp/a7_source_context/.claude/plans/Drivers/experiments}" \
      A7_SOURCE_PROJECTS="${A7_SOURCE_PROJECTS:-/tmp/a7_logs_1781/attempt_life2/TEST_projects}" \
      A7_SEALED_PACKAGE="${A7_SEALED_PACKAGE:-$A/unit_1888/logs/inventory_review}" \
      GIT_DIR="/home/faisal/EventMarketDB/.git" \
    "$PY" -B "$BND" --host "$U/$MAP" "$U/ledger/$PAYLOAD" \
    > "$ATT/stdout.txt" 2> "$ATT/stderr.txt" < /dev/null &
WRAP=$!
LEADER=""
for _ in 1 2 3 4 5; do LEADER=$(pgrep -P "$WRAP" | head -1); [ -n "$LEADER" ] && break; sleep 0.2; done
{ printf 'attempt\t%s\npayload\t%s\nmap\t%s\n' "$TAG" "$PAYLOAD" "$MAP"
  printf 'command\trun_1957.sh %s %s %s %s\n' "$MAP" "$PAYLOAD" "$TAG" "$LIMIT"
  printf 'wrapper_pid\t%s\npayload_pid\t%s\npayload_pgid\t%s\n' "$WRAP" "$LEADER" \
    "$([ -n "$LEADER" ] && ps -o pgid= -p "$LEADER" 2>/dev/null | tr -d ' ')"
  printf 'started_utc\t%s\nstate\trunning\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$ATT/owner.tsv"
wait "$WRAP"
RC=$?
echo "$RC" > "$ATT/exit"
python3 - "$ATT/owner.tsv" "$RC" <<'PY'
import io, sys
p, rc = sys.argv[1], sys.argv[2]
t = io.open(p, encoding="utf-8").read().replace("state\trunning", "state\tfinished exit %s" % rc)
io.open(p, "w", encoding="utf-8").write(t)
PY
cat "$ATT/stdout.txt"; echo "--- stderr tail ---"; tail -8 "$ATT/stderr.txt"; echo "raw exit $RC"
exit "$RC"
