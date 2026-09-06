#!/bin/bash
# Compose the G1 read-only views from EXACT published bytes plus this unit's own
# new G1 evidence (Codex SEQ 1778 item 2). The old unit_1773 view is never
# modified; this is a separate composition that ADDS the G1 sources it lacks.
#
#   workflows     = published session store + published producer states + new G1 states
#   subagent_runs = published session store + published producer runs   + new G1 runs
#
# usage: compose_views_1778.sh <recovery-root> <unit-dir>
set -euo pipefail
R="${1:?recovery root}"; U="${2:?unit dir}"
SS="$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/session_store/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
P="$R/a7_recovery/unit_1773/evidence"
rm -rf "$U/view/workflows" "$U/view/subagent_runs"
mkdir -p "$U/view/workflows" "$U/view/subagent_runs"
cp -a "$SS/workflows/."          "$U/view/workflows/"
cp -a "$P/producer_states/."     "$U/view/workflows/"
cp -a "$U/evidence/g1_states/."  "$U/view/workflows/"
cp -a "$SS/subagents/workflows/." "$U/view/subagent_runs/"
cp -a "$P/producer_runs/."        "$U/view/subagent_runs/"
cp -a "$U/evidence/g1_runs/."     "$U/view/subagent_runs/"
echo "composed: workflows=$(ls "$U/view/workflows" | wc -l) subagent_runs=$(ls "$U/view/subagent_runs" | wc -l)"
