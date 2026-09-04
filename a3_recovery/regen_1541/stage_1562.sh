#!/bin/bash
# STAGE - never commit - the corrective A3 checkpoint on the recovery branch (Codex SEQ 1562
# item 4). Refreshes the worktree copy from the frozen package with modes preserved, stages the
# compact proof plus the IRREPLACEABLE results - the 392+1 raw replies, the parsed answers, the
# ordered log, the 38 states and 38 transcripts the strict identity proof reads, the signer
# evidence - writes the publication manifest from the index, and proves that an export of the
# index is byte-exact and runnable. The commit waits for Codex VERIFIED.
set -eu
shopt -s nullglob   # an empty pattern vanishes instead of aborting a whole git add
P="$(cd "$(dirname "$0")" && pwd)"
PY=/home/faisal/EventMarketDB/venv/bin/python
W=/home/faisal/EventMarketDB-driver-recovery
D=a3_recovery/regen_1541
LOG="${1:-ordered_1562.txt}"
cd "$W"
[ "$(git branch --show-current)" = recovery/a3-a7-verified ] || { echo "REFUSED: not on recovery/a3-a7-verified"; exit 2; }
git diff --cached --quiet || { echo "REFUSED: the index already carries staged changes"; exit 2; }
[ -n "$(git ls-files -- "$D" | head -1)" ] || { echo "REFUSED: $D is not the tracked copy"; exit 2; }
echo "== provisional checkpoint HEAD $(git rev-parse HEAD) stays; refreshing the copy $D from the frozen package"
rm -rf "$D"
$PY "$P/copy_accepted_package.py" "$LOG"
# THE COMPACT PROOF: code, tests, manifests, reports, evidence tables, the run's identity files
git add "$D"/*.py "$D"/*.sh "$D"/PACKAGE_MANIFEST.tsv "$D"/ORDERED_LOG.sha256 "$D"/ORDERED_LOG.txt "$D"/tests "$D"/proofs "$D"/ledger "$D"/reports
git add "$D"/products
# the receipt reconstructions' inputs (steps 6/6b) and the accepted-checkpoint evidence (step 4): compact chain inputs
git add "$D"/a3_work "$D"/recovered
git add "$D"/evidence/*.tsv "$D"/evidence/*.json "$D"/evidence/git_bases/*.json "$D"/evidence/git_bases/GIT_BASES.tsv "$D"/evidence/git_bases/*.tree \
        "$D"/evidence/workflow_states/WORKFLOW_STATES.tsv "$D"/evidence/subagent_records/SUBAGENT_RECORDS.tsv
git add "$D"/bench/.claude/plans/Drivers/experiments/invrev_run4 "$D"/bench/.claude/plans/Drivers/experiments/a3_serial_dir.txt \
        "$D"/bench/.claude/plans/Drivers/experiments/runs/a3_serial_run/*.json "$D"/bench/.claude/plans/Drivers/experiments/runs/a3_serial_run/launch \
        "$D"/bench/.claude/plans/Drivers/experiments/lock
git add "$D"/evidence/a3_* "$D"/evidence/*.py "$D"/evidence/*.md "$D"/evidence/*.js
# THE MEASURED CLOSURE OF THE REAL PATH (evidence/CLOSURE.tsv, from closure_trace.py): every
# projection row - the 392+1 raw replies and answers, the launchers, receipts and
# finalizations, the 75 official states and 431 agent transcripts, the keys and the
# inventory package - plus every code and data file the path's processes opened; the
# signer evidence beside it. Not the derived sibling cache, not the git store, not the
# transcript prefix: those are regenerable or live-durable and measured so.
git add "$D"/evidence/signer
$PY - "$P" "$D" <<'PYROWS' | xargs -d '\n' git add
import os, sys
sys.path.insert(0, sys.argv[1])
import closure_trace as CT
for rel in sorted(CT.load(sys.argv[1])):
    print(os.path.join(sys.argv[2], rel))
PYROWS
# THE PACKAGE'S OWN MANIFEST, FOR THE COMPACT EXPORT: regenerated inside an export of the
# staged index and staged back, so the shipped freeze_package.py --verify accepts the
# checkout it ships in; then the publication manifest, whose row for it changed
$PY - "$W" <<'PYMAN'
import sys
sys.path.insert(0, "/home/faisal/.core827_backups/recovery_1531/regen_1541")
import write_publication_manifest as WPM
WPM.refresh_internal_manifest(sys.argv[1])
PYMAN
$PY "$P/write_publication_manifest.py" "$W"
git add a3_recovery/PUBLICATION_MANIFEST.tsv
echo "== STAGED tree $(git write-tree) on branch $(git branch --show-current), HEAD $(git rev-parse HEAD) unchanged, nothing committed"
git diff --cached --stat | tail -1
echo "staged paths: $(git diff --cached --name-only | wc -l) | executable in the index: $(git ls-files -s -- "$D" | awk '$1=="100755"' | wc -l)"
# THE CHECKOUT PROOF: the index exported alone, verified static, then the real path executed in it
$PY "$P/verify_checkout.py" "$W" --execute
