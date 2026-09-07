#!/bin/bash
# Rebuild this unit's two read-only views from bytes the tree already carries,
# so neither is duplicated into the publication.
#
#   workflows      = unit_1792's published 625-file view
#                    + the ONE official state unit_1802 captured for this run
#   subagent_runs  = unit_1778's published 624 run directories (hard-linked, so
#                    no bytes are copied) + unit_1802's captured agent directory
#                    for this run
#
# usage: compose_views_1803.sh <recovery-root> <destination-unit-dir>
set -euo pipefail
R="${1:?recovery root}"; D="${2:?destination unit dir}"
A="$R/a7_recovery"
mkdir -p "$D/view"
cp -a  "$A/unit_1792/view/workflows"        "$D/view/workflows"
cp -a  "$A/unit_1802/capture/after/wf_feabb3a2-628.json" "$D/view/workflows/"
cp -al "$A/unit_1778/view/subagent_runs"    "$D/view/subagent_runs"
cp -a  "$A/unit_1802/capture/after/wf_feabb3a2-628"      "$D/view/subagent_runs/"
