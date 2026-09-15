#!/bin/bash
set -o pipefail
env PYTHONDONTWRITEBYTECODE=1 /home/faisal/EventMarketDB/venv/bin/python3 -B a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher/boundary.py --host a7_recovery/unit_2020_codex_check/map_current_key_2148.tsv a7_recovery/unit_2020_codex_check/trace_corrected_score_2167.py | jq -c .
