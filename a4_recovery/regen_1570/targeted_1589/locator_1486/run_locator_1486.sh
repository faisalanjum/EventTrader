#!/bin/bash
# THE RECOVERY WORLD for the SEQ 1486 locator receipt (Codex SEQ 1592): the accepted A4 foundation
# world (its projection plus foundation/out/12) and the stage-1 harness_g1v3 tree, inside one private
# mount namespace; real /tmp, the live store, the mailbox, the backups, regen_1566 and the main checkout
# are masked. Nothing durable is written under /tmp; the adapter exports to <here>/out.
#   run_locator_1486.sh all     red (old projection), green (derived projections), then the mutation tests
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$HERE/../.." && pwd)"
mkdir -p "$HERE/out"
unshare -rm --propagation private /bin/bash -s "$HERE" "$R" <<'INNER'
set -u
HERE="$1"; R="$2"
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1 LOCATOR_1486_HOME="$HERE"
S=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad
SESS=/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200
MAIN=/home/faisal/EventMarketDB
R66=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1566
STAGE1=/home/faisal/.core827_backups/recovery_1531/regen_1539/builds/stage1/tree/.claude/plans/Drivers/experiments/harness_g1v3
mount -t tmpfs none /tmp || { echo "NS: private /tmp failed"; exit 3; }
mkdir -p /tmp/venv_real && mount --bind "$MAIN/venv" /tmp/venv_real || exit 3
mkdir -p /tmp/gitobj_real && mount --bind "$MAIN/.git/objects" /tmp/gitobj_real || exit 3
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
mount -t tmpfs none "$MAIN" || exit 3
mkdir -p "$MAIN/venv" && mount --bind /tmp/venv_real "$MAIN/venv" && mount -o remount,bind,ro "$MAIN/venv" && umount /tmp/venv_real && rmdir /tmp/venv_real || exit 3
# the stage-1 harness tree is staged before the backups are masked
cp -a "$STAGE1" /tmp/harness_g1v3_stage1 || exit 3
for d in "$SESS/workflows" "$SESS/subagents/workflows" "$SESS/memory" "$HOME/.core827-orchestrator" "$HOME/.core827_backups" "$R66"; do
  mkdir -p "$d" && mount -t tmpfs none "$d" || { echo "NS: mask of $d failed"; exit 3; }
done
(cd "$R" && $PY -B foundation_sources.py project "$R/inputs/FOUNDATION_PROJECTION.tsv") || { echo "NS: projection refused"; exit 4; }
G="$S/bench_1306/.git"
mkdir -p "$G/objects" "$G/refs" && printf 'ref: refs/heads/main\n' > "$G/HEAD" && mount --bind /tmp/gitobj_real "$G/objects" && mount -o remount,bind,ro "$G/objects" && umount /tmp/gitobj_real && rmdir /tmp/gitobj_real || exit 3
# the accepted built world: the A4 phase runs and packages, the phase-1 pointer, the scratch a4 dir
cp -a "$R/foundation/out/12/bench_1306/." "$S/bench_1306/" || exit 3
mkdir -p "$S/a4" && cp -a "$R/foundation/out/12/a4/." "$S/a4/" && cp "$R/foundation/out/12/a4_dir.txt" "$S/a4_dir.txt" || exit 3
# the final inventory epoch, as the accepted world holds it after its inventory stage
cp "$R/foundation/a3/bench/.claude/plans/Drivers/experiments/one_item_benchmark_inventory.json" "$S/bench_1306/.claude/plans/Drivers/experiments/one_item_benchmark_inventory.json" || exit 3
mkdir -p "$S/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3" && cp -a /tmp/harness_g1v3_stage1/. "$S/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/" && rm -rf /tmp/harness_g1v3_stage1 || exit 3
export GUIDANCE_SCRIPTS_DIR="$S/bench_1306/.claude/skills/earnings-orchestrator/scripts"
cd "$S/bench_1306"
echo "== RED $(date +%T)"; $PY -B "$HERE/recovery_adapter.py" red > "$HERE/out/red.txt" 2>&1; rrc=$?; tail -2 "$HERE/out/red.txt"; echo "red rc=$rrc"
echo "== GREEN $(date +%T)"; $PY -B "$HERE/recovery_adapter.py" green > "$HERE/out/green.txt" 2>&1; grc=$?; tail -9 "$HERE/out/green.txt"; echo "green rc=$grc"
echo "== TESTS $(date +%T)"; (cd /tmp && $PY -B -m pytest -p no:cacheprovider --import-mode=importlib -q -v -s "$HERE/test_locator_1486.py") > "$HERE/out/mutations.txt" 2>&1; trc=$?; grep -c "PASSED" "$HERE/out/mutations.txt"; tail -3 "$HERE/out/mutations.txt"; echo "tests rc=$trc"
echo "== DONE $(date +%T) red=$rrc green=$grc tests=$trc"
exit $(( rrc + grc + trc ))
INNER
