#!/bin/bash
# Rebuild this unit's two read-only views into NEW ABSENT destinations from
# bytes the tree already carries, so neither is duplicated into the publication.
#
#   workflows      = unit_1808's view + the ONE official state this unit captured
#   subagent_runs  = unit_1808's view (hard-linked, no bytes copied)
#                    + this unit's captured agent directory for the same run
#
# usage: compose_views_1814.sh <recovery-root> <destination-unit-dir>
set -euo pipefail
R="${1:?recovery root}"; D="${2:?destination unit dir}"
A="$R/a7_recovery"
mkdir -p "$D/view"
cp -a  "$A/unit_1808/view/workflows"     "$D/view/workflows"
cp -a  "$A/unit_1814/capture/after/wf_b0543d14-6c2.json" "$D/view/workflows/"
cp -al "$A/unit_1808/view/subagent_runs" "$D/view/subagent_runs"
cp -a  "$A/unit_1814/capture/after/wf_b0543d14-6c2"      "$D/view/subagent_runs/"
