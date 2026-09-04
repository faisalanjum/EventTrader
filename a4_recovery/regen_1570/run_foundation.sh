#!/bin/bash
# The A4 foundation inside one private mount namespace projected from the candidate alone (Codex SEQ
# 1579 item 3, 1581): real /tmp, the live official store, the mailbox, the backups, regen_1566 and the
# main checkout are masked (the venv is re-bound read-only for the interpreter; only the repository object store
# is bound read-only at the bench, with global and system Git configuration disabled, so the review-package owner can
# derive the frozen base tree); every projection row
# is copied to its historical path and verified before and after the run. Nothing durable is written
# under /tmp and no mount survives the namespace.
#   run_foundation.sh run <n> [--trace] [--tests]   build number n into foundation/out/<n> (strace closure optional;
#                                             --tests runs tests/test_v6_world.py on the built world, to <n>/world_tests.txt,
#                                             before the completion marker; a failing test is the exit status)
#   run_foundation.sh red                   the RED probes against the preliminary A4 view
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-run}"; N="${2:-1}"; TRACE="${3:-}"; TESTS="${4:-}"
[ "$MODE" = run ] && mkdir -p "$HERE/foundation/out/$N"
unshare -rm --propagation private /bin/bash -s "$HERE" "$MODE" "$N" "$TRACE" "$TESTS" <<'INNER'
set -u
HERE="$1"; MODE="$2"; N="$3"; TRACE="$4"; TESTS="$5"
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1
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
for d in "$SESS/workflows" "$SESS/subagents/workflows" "$SESS/memory" "$HOME/.core827-orchestrator" "$HOME/.core827_backups" "$R66"; do
  mkdir -p "$d" && mount -t tmpfs none "$d" || { echo "NS: mask of $d failed"; exit 3; }
done
TABLE="$HERE/inputs/FOUNDATION_PROJECTION.tsv"
(cd "$HERE" && $PY -B foundation_sources.py project "$TABLE") || { echo "NS: projection refused"; exit 4; }
# the narrow read-only Git identity input: ONLY the repository object store, at the bench's object path, plus the
# minimum deterministic private control git needs to resolve a commit (a HEAD line and an empty refs dir), written here
G="$S/bench_1306/.git"
mkdir -p "$G/objects" "$G/refs" && printf 'ref: refs/heads/main\n' > "$G/HEAD" && mount --bind /tmp/gitobj_real "$G/objects" && mount -o remount,bind,ro "$G/objects" && umount /tmp/gitobj_real && rmdir /tmp/gitobj_real || exit 3
if [ "$MODE" = red ]; then
  # RED only: the preliminary A4 view reconstructed at the harness path from the committed A3 package's
  # later launch manifest and the corrected key owner alone (no baseline exists yet), never from the candidate
  A3PKG=/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541/bench/.claude/plans/Drivers/experiments/harness
  cp "$A3PKG/build_launch_manifest.py" "$S/bench_1306/.claude/plans/Drivers/experiments/harness/build_launch_manifest.py"
  cp "$HERE/foundation/owners/build_kfields_key.a289601b.py" "$S/bench_1306/.claude/plans/Drivers/experiments/harness/build_kfields_key.py"
fi
: > "$S/.foundation_projection"
[ "$MODE" = red ] || (cd "$HERE" && $PY -B foundation_sources.py verify-view "$TABLE") || { echo "NS: projected view refused"; exit 5; }
export GUIDANCE_SCRIPTS_DIR="$S/bench_1306/.claude/skills/earnings-orchestrator/scripts"
cd "$S/bench_1306"
if [ "$MODE" = red ]; then $PY -B "$HERE/foundation.py" red-probe; exit $?; fi
OUT="$HERE/foundation/out/$N"
if [ -n "$TRACE" ]; then
  strace -f -e trace=openat,execve -o "$OUT.strace" $PY -B "$HERE/foundation.py" run "$OUT"; rc=$?
  mkdir -p "$OUT" && mv "$OUT.strace" "$OUT/closure.strace"
else
  $PY -B "$HERE/foundation.py" run "$OUT"; rc=$?
fi
[ $rc -eq 0 ] || { echo "FOUNDATION REFUSED rc=$rc"; exit $rc; }
(cd "$HERE" && $PY -B foundation_sources.py verify-view "$TABLE" --after-run) || { echo "NS: view after the run refused"; exit 6; }
if [ -n "$TRACE" ]; then
  (cd "$HERE" && $PY -B foundation_closure.py "$OUT/closure.strace" "$TABLE" "$OUT/CLOSURE.tsv") > "$OUT/closure.txt" 2>&1 || { cat "$OUT/closure.txt"; exit 7; }
  cat "$OUT/closure.txt"
fi
if [ -n "$TESTS" ]; then
  # the real owner boundaries on the built world (each mutation restored by its test); the accepted export above is untouched;
  # a failing test is this wrapper's exit status and no completion marker is written
  (cd "$HERE" && $PY -B -m pytest -p no:cacheprovider --import-mode=importlib -q tests/test_v6_world.py) > "$OUT/world_tests.txt" 2>&1; trc=$?
  echo "world tests rc=$trc : $(tail -1 "$OUT/world_tests.txt")"
  [ $trc -eq 0 ] || exit 8
fi
if [ -n "$TRACE" ]; then
  # the one success marker: written only after the post-run view, the closure and (when asked) the world tests all passed
  printf 'tree %s\n%s\n' "$(sha256sum "$OUT/TREE.tsv" | cut -d' ' -f1)" "$(head -1 "$OUT/closure.txt")" > "$OUT/COMPLETE"
fi
exit 0
INNER
