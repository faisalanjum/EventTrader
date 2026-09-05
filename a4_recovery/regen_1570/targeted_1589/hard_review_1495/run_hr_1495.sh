#!/bin/bash
# THE RECOVERY WORLD for the hard-review run 1495 (Codex SEQ 1608), derived from the accepted run-1491 wrapper: the A4 foundation world
# (its projection plus foundation/out/12), the final inventory epoch, and this unit's immutable inputs/ tree
# (the stage-1 harness_g1v3 with the era transport), inside one private mount namespace; real /tmp, the live
# store, the mailbox, the backups, regen_1566 and the main checkout are masked; nothing is read from a backup
# root. World A runs the adapter and the focused tests once; world B is a separate fresh build. The wrapper
# fails closed on any adapter or test failure and on any A/B byte difference.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$HERE/../.." && pwd)"; OUTROOT="$HERE/out/attempt10"
mkdir -p "$OUTROOT"
world() {
unshare -rm --propagation private /bin/bash -s "$HERE" "$R" "$1" "$2" "$OUTROOT" <<'INNER'
set -u
HERE="$1"; R="$2"; TAG="$3"; TESTS="$4"; OUTROOT="$5"
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1 PHASE1_1488_HOME="$HERE/../phase1_targeted_1488" RUN_1491_HOME="$HERE/../targeted_run_1491" HR_1495_HOME="$HERE"
S=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad
SESS=/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200
MAIN=/home/faisal/EventMarketDB
R66=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1566
mount -t tmpfs none /tmp || { echo "NS: private /tmp failed"; exit 3; }
mkdir -p /tmp/venv_real && mount --bind "$MAIN/venv" /tmp/venv_real || exit 3
mkdir -p /tmp/gitobj_real && mount --bind "$MAIN/.git/objects" /tmp/gitobj_real || exit 3
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
mount -t tmpfs none "$MAIN" || exit 3
mkdir -p "$MAIN/venv" && mount --bind /tmp/venv_real "$MAIN/venv" && mount -o remount,bind,ro "$MAIN/venv" && umount /tmp/venv_real && rmdir /tmp/venv_real || exit 3
for d in "$(dirname "$SESS")" "$HOME/.core827-orchestrator" "$HOME/.core827_backups" "$R66" ${MASK_EXTRA:-}; do
  mkdir -p "$d" && mount -t tmpfs none "$d" || { echo "NS: mask of $d failed"; exit 3; }
done
mkdir -p "$SESS/workflows" "$SESS/subagents/workflows" || exit 3
(cd "$R" && $PY -B foundation_sources.py project "$R/inputs/FOUNDATION_PROJECTION.tsv") || { echo "NS: projection refused"; exit 4; }
G="$S/bench_1306/.git"
mkdir -p "$G/objects" "$G/refs" && printf 'ref: refs/heads/main\n' > "$G/HEAD" && mount --bind /tmp/gitobj_real "$G/objects" && mount -o remount,bind,ro "$G/objects" && umount /tmp/gitobj_real && rmdir /tmp/gitobj_real || exit 3
cp -a "$R/foundation/out/12/bench_1306/." "$S/bench_1306/" || exit 3
mkdir -p "$S/a4" && cp -a "$R/foundation/out/12/a4/." "$S/a4/" && cp "$R/foundation/out/12/a4_dir.txt" "$S/a4_dir.txt" || exit 3
cp "$R/foundation/a3/bench/.claude/plans/Drivers/experiments/one_item_benchmark_inventory.json" "$S/bench_1306/.claude/plans/Drivers/experiments/one_item_benchmark_inventory.json" || exit 3
H="$S/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
mkdir -p "$H" && cp -a "$HERE/../phase1_targeted_1488/inputs/harness_g1v3/." "$H/" || exit 3
export GUIDANCE_SCRIPTS_DIR="$S/bench_1306/.claude/skills/earnings-orchestrator/scripts"
echo "== WORLD $TAG $(date +%T) masks: $(findmnt -rn -t tmpfs | wc -l) tmpfs"; $PY -B "$HERE/recover_hr_1495.py" "$TAG" > "$OUTROOT/${TAG}_adapter.txt" 2>&1; arc=$?; tail -30 "$OUTROOT/${TAG}_adapter.txt"; echo "adapter rc=$arc"
trc=0
if [ "$TESTS" = 1 ] && [ $arc -eq 0 ]; then
  (cd /tmp && $PY -B -m pytest -p no:cacheprovider --import-mode=importlib -q -v "$HERE/test_hr_1495.py") > "$OUTROOT/${TAG}_tests.txt" 2>&1; trc=$?
  tail -3 "$OUTROOT/${TAG}_tests.txt"; echo "tests rc=$trc"
  # Codex SEQ 1614 item 2: the one required public-door control of the era suite, run from the harness; nothing else of that suite
  (cd "$H" && $PY -B -m pytest -p no:cacheprovider -q --tb=line "test_a4_hard_review_targeted_1492.py::test_the_public_doors_are_fixed_and_the_historical_ones_unchanged") > "$OUTROOT/${TAG}_door_test.txt" 2>&1; drc=$?
  tail -3 "$OUTROOT/${TAG}_door_test.txt"; echo "public-door test rc=$drc"; trc=$(( trc + drc ))
fi
echo "== DONE $TAG $(date +%T) adapter=$arc tests=$trc"
exit $(( arc + trc ))
INNER
}
world A ${HR_TESTS:-1}; ra=$?
world B 0; rb=$?
(cd "$OUTROOT" && diff -rq A B > COMPARE.txt 2>&1; drc=$?; echo "diff rc=$drc" >> COMPARE.txt; for w in A B; do find $w -type f | sort | while read f; do printf "%s  %s\n" "$(sha256sum "$f" | cut -c1-64)" "${f#$w/}"; done > $w.sha; done; exit $drc); dc=$?
echo "== COMPARE"; cat "$OUTROOT/COMPARE.txt"; echo "== ALL DONE A=$ra B=$rb diff=$dc"
[ $ra -eq 0 ] && [ $rb -eq 0 ] && [ $dc -eq 0 ] || { echo "GATE FAIL-CLOSED"; exit 9; }
echo "GATE PASS"; exit 0
