#!/bin/bash
# Rebuild the two composed read-only views from EXACT published bytes plus this
# unit's own newly whitelisted evidence (Codex SEQ 1774 item 2).
#
# Neither view is published as a directory: each is the union of an already
# published old forest and this run's own records, so publishing them again
# would duplicate ~318 MB of bytes the tree already carries.
#
#   view/workflows      = published session store workflows   + evidence/producer_states
#   view/subagent_runs  = published session store subagents   + evidence/producer_runs
#
# usage: compose_views_1773.sh <recovery-root> <unit-dir>
set -euo pipefail
R="${1:?recovery root}"; U="${2:?unit dir}"
SS="$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/session_store/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"

rm -rf "$U/view/workflows" "$U/view/subagent_runs"
mkdir -p "$U/view/workflows" "$U/view/subagent_runs"
cp -a "$SS/workflows/." "$U/view/workflows/"
cp -a "$U/evidence/producer_states/." "$U/view/workflows/"
cp -a "$SS/subagents/workflows/." "$U/view/subagent_runs/"
cp -a "$U/evidence/producer_runs/." "$U/view/subagent_runs/"
echo "composed: workflows=$(ls "$U/view/workflows" | wc -l) subagent_runs=$(ls "$U/view/subagent_runs" | wc -l)"
