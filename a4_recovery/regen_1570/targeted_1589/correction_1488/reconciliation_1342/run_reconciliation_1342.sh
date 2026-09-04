#!/bin/bash
# THE RECOVERY WORLD for the reviewed reconciliation replay (Codex SEQ 1596): the accepted A4 foundation
# projection inside one private mount namespace; real /tmp, the live store, the mailbox, the backups,
# regen_1566 and the main checkout are masked; the archived instruction is projected into the masked
# mailbox by the adapter. Two fresh worlds (A, B) export to <here>/out/A and out/B; then every byte is compared.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$HERE/../../.." && pwd)"
mkdir -p "$HERE/out"
world() {
unshare -rm --propagation private /bin/bash -s "$HERE" "$R" "$1" <<'INNER'
set -u
HERE="$1"; R="$2"; TAG="$3"
PY=/home/faisal/EventMarketDB/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1 RECON_1342_HOME="$HERE"
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
(cd "$R" && $PY -B foundation_sources.py project "$R/inputs/FOUNDATION_PROJECTION.tsv") || { echo "NS: projection refused"; exit 4; }
G="$S/bench_1306/.git"
mkdir -p "$G/objects" "$G/refs" && printf 'ref: refs/heads/main\n' > "$G/HEAD" && mount --bind /tmp/gitobj_real "$G/objects" && mount -o remount,bind,ro "$G/objects" && umount /tmp/gitobj_real && rmdir /tmp/gitobj_real || exit 3
cp -a "$R/foundation/out/12/bench_1306/." "$S/bench_1306/" || exit 3
mkdir -p "$S/a4" && cp -a "$R/foundation/out/12/a4/." "$S/a4/" && cp "$R/foundation/out/12/a4_dir.txt" "$S/a4_dir.txt" || exit 3
echo "== WORLD $TAG $(date +%T)"; $PY -B "$HERE/replay_1342.py" "$TAG" > "$HERE/out/${TAG}_adapter.txt" 2>&1; arc=$?; tail -30 "$HERE/out/${TAG}_adapter.txt"; echo "adapter rc=$arc"
echo "== DONE $TAG $(date +%T) adapter=$arc"
exit $arc
INNER
}
world A; ra=$?
world B; rb=$?
(cd "$HERE/out" && diff -rq A B > COMPARE.txt 2>&1; echo "diff rc=$?" >> COMPARE.txt; for w in A B; do find $w -type f | sort | while read f; do printf "%s  %s\n" "$(sha256sum "$f" | cut -c1-64)" "${f#$w/}"; done > $w.sha; done)
echo "== COMPARE"; cat "$HERE/out/COMPARE.txt"; echo "== ALL DONE A=$ra B=$rb"
exit $(( ra + rb ))
