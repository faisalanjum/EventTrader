#!/bin/bash
# Rebuild this unit's read-only workflow-state view from THREE already-published
# layers, in this exact order (Codex SEQ 1782 item 2). No published unit is
# modified and nothing is duplicated into the publication: the 624 files are
# reachable from bytes the tree already carries.
#
#   layer 1  A4 session-store workflows        583 files
#   layer 2  unit_1773 producer states          36 files
#   layer 3  unit_1778 G1 states                 5 files
#
# usage: compose_views_1781.sh <recovery-root> <destination-dir>
set -euo pipefail
R="${1:?recovery root}"; D="${2:?destination}"
L1="$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/session_store/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows"
L2="$R/a7_recovery/unit_1773/evidence/producer_states"
L3="$R/a7_recovery/unit_1778/evidence/g1_states"
mkdir -p "$D"
cp -a "$L1/." "$D/"
cp -a "$L2/." "$D/"
cp -a "$L3/." "$D/"
echo "layers: $(ls "$L1" | wc -l) + $(ls "$L2" | wc -l) + $(ls "$L3" | wc -l) -> $(ls "$D" | wc -l) files"
