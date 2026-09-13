#!/bin/bash
# Codex SEQ 2081: one named launcher for this unit. Launches no model call.
set -u
A=/home/faisal/EventMarketDB-driver-recovery/a7_recovery
M=$A/unit_2081_final_key_candidate
export A7_LANE_INPUT_PROFILES=/tmp/a7_lane_input_profiles.json
export A7_SOURCE_PROJECTS=/home/faisal/.claude/projects
export A7_REVIEW_OUT=/tmp/a7_real_package_1947
export A7_SOURCE_CONTEXT=/tmp/a7_source_context
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000
export PYTHONDONTWRITEBYTECODE=1
cd $A/unit_1947/ledger || exit 2
run(){ tag=$1; map=$2; pay=$3; shift 3
  env "$@" PYTHONDONTWRITEBYTECODE=1 A7_TAG=$tag A7_RUN_BINDING=$M/$map bash ./run_real_1947.sh \
      ../unit_2081_final_key_candidate/$map $pay $tag "${LIMIT:-1800}" >/dev/null 2>&1
  e=$(cat $A/unit_1947/logs/attempt_$tag/exit)
  p=$(grep -c '^PASS' $A/unit_1947/logs/attempt_$tag/stdout.txt 2>/dev/null || true)
  u=$(grep -oP 'Ran \d+ tests in [0-9.]+s' $A/unit_1947/logs/attempt_$tag/stderr.txt 2>/dev/null | tail -1)
  o=$(grep -oP '^(OK|FAILED.*)$' $A/unit_1947/logs/attempt_$tag/stderr.txt 2>/dev/null | tail -1)
  printf '%-26s exit=%s PASS=%s %s %s\n' "$tag" "$e" "$p" "$u" "$o"
}
run "$@"
