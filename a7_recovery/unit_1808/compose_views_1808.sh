#!/bin/bash
# Rebuild this unit's two read-only views into NEW ABSENT destinations from
# bytes the tree already carries, so neither is duplicated into the publication.
#
#   workflows      = unit_1806's view + the ONE official state this unit captured
#   subagent_runs  = unit_1806's view (hard-linked, no bytes copied)
#                    + this unit's captured agent directory for the same run
#
# usage: compose_views_1808.sh <recovery-root> <destination-unit-dir>
set -euo pipefail
R="${1:?recovery root}"; D="${2:?destination unit dir}"
A="$R/a7_recovery"
mkdir -p "$D/view"
cp -a  "$A/unit_1806/view/workflows"     "$D/view/workflows"
cp -a  "$A/unit_1808/capture/after/wf_317ef88a-df4.json" "$D/view/workflows/"
cp -al "$A/unit_1806/view/subagent_runs" "$D/view/subagent_runs"
cp -a  "$A/unit_1808/capture/after/wf_317ef88a-df4"      "$D/view/subagent_runs/"
