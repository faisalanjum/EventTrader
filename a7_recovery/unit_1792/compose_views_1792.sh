#!/bin/bash
# Rebuild this unit's read-only workflow-state view without duplicating it.
# It is unit_1781's already-published 624-file view plus the ONE official state
# the resumed batch wrote, which unit_1786 carries in its capture. unit_1786 is
# published by the SAME checkpoint as this unit, not before it. Nothing is
# duplicated into this publication and no published unit is modified.
#
#   usage: compose_views_1792.sh <recovery-root> <destination-dir>
set -euo pipefail
R="${1:?recovery root}"; D="${2:?destination}"
bash "$R/a7_recovery/unit_1781/compose_views_1781.sh" "$R" "$D"
cp -a "$R/a7_recovery/unit_1786/capture/after/wf_41b934cf-f76.json" "$D/"
