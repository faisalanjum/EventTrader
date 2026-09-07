#!/bin/bash
# Rebuild this unit's two read-only views into NEW ABSENT destinations, from
# bytes the tree already carries, so neither is duplicated into the publication.
#
#   workflows      = unit_1803's view + the ONE official state unit_1805 captured
#   subagent_runs  = unit_1803's view (hard-linked, so no bytes are copied)
#                    + unit_1805's captured agent directory for that run
#
# usage: compose_views_1806.sh <recovery-root> <destination-unit-dir>
set -euo pipefail
R="${1:?recovery root}"; D="${2:?destination unit dir}"
A="$R/a7_recovery"
mkdir -p "$D/view"
cp -a  "$A/unit_1803/view/workflows"     "$D/view/workflows"
cp -a  "$A/unit_1805/capture/after/wf_ea5fdfab-8e9.json" "$D/view/workflows/"
cp -al "$A/unit_1803/view/subagent_runs" "$D/view/subagent_runs"
cp -a  "$A/unit_1805/capture/after/wf_ea5fdfab-8e9"      "$D/view/subagent_runs/"
