#!/bin/bash
# The real A3 finalization and resume path at the ORIGINAL run-directory path, inside a
# private mount namespace whose ENTIRE /tmp is a tmpfs projected from manifested package
# bytes (Codex SEQ 1561 item 1). The receipt binds the run to its historical absolute
# path; that path is reproduced here from the package alone. The real /tmp is hidden and
# unread: nothing in it is visible, nothing is written to it.
#
# WHAT MAY APPEAR IN THE PROJECTION is exactly evidence/PROJECTION.tsv (built from the
# freeze's own walk by project_historical_tree.py): each row is copied to its historical
# path and re-verified; after the run the projected tree is verified again, so a file the
# run generated is lawful only if it is byte-identical to a manifested package file
# (the 36+1 armed launchers, the receipts the arming republishes, the finalizations).
#
# "materialise" mode is the ONE-TIME step that vendors the armed launchers into the
# package so that later runs are verified against them. Every other run is a proof.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-prove}"
PY=/home/faisal/EventMarketDB/venv/bin/python
read -r EV RUN < <(PYTHONDONTWRITEBYTECODE=1 $PY -c "import project_historical_tree as P; print(*P.historical_roots())" 2>/dev/null || echo "" "")
[ -n "$EV" ] && [ -n "$RUN" ] || { echo "NS: no historical roots from the receipt"; exit 3; }

unshare -rm --propagation private /bin/bash -s "$HERE" "$EV" "$RUN" "$MODE" <<'INNER'
set -u
HERE="$1"; EV="$2"; RUN="$3"; MODE="$4"
PY=/home/faisal/EventMarketDB/venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
mount -t tmpfs none /tmp || { echo "NS: tmpfs mount over /tmp failed"; exit 3; }
# THE LIVE SESSION RECORDS AND THE MAILBOX ARE MASKED: the receipts' official states are
# projected from their manifested copies at the very same paths, and the source-gap
# search finds an empty mailbox directory rather than the live one
SROOT="$(cd "$HERE" && PYTHONDONTWRITEBYTECODE=1 $PY -c "import project_historical_tree as P; print(P.states_root())")"
mkdir -p "$SROOT" 2>/dev/null
mount -t tmpfs none "$SROOT" || { echo "NS: tmpfs mount over the states dir failed"; exit 3; }
RROOT="$(cd "$HERE" && PYTHONDONTWRITEBYTECODE=1 $PY -c "import project_historical_tree as P; print(P.records_root())")"
mkdir -p "$RROOT" 2>/dev/null
mount -t tmpfs none "$RROOT" || { echo "NS: tmpfs mount over the records dir failed"; exit 3; }
[ -d "$HOME/.core827-orchestrator" ] && { mount -t tmpfs none "$HOME/.core827-orchestrator" || { echo "NS: mailbox mask failed"; exit 3; }; }
# PROJECT: every row of the table, copied to its historical path from the package
$PY - "$HERE" <<'PYP'
import io, os, shutil, sys
here = sys.argv[1]; sys.path.insert(0, here)
import project_historical_tree as P
for ph, hist, rel, _b, _s in P.load():
    if ph == "identity":
        continue                       # the run directory is what the run must GENERATE
    os.makedirs(os.path.dirname(hist), exist_ok=True)
    shutil.copyfile(os.path.join(here, rel), hist)
bad = P.verify(phase="input")
print("PROJECTED %d input files; defects before the run: %d" % (sum(1 for r in P.load() if r[0] == "input"), len(bad)))
for b in bad[:5]: print("  DEFECT", b)
raise SystemExit(1 if bad else 0)
PYP
[ $? -eq 0 ] || { echo "NS: projection refused"; exit 3; }
H="$HERE/bench/.claude/plans/Drivers/experiments/harness"
cd "$H"
GUIDANCE_SCRIPTS_DIR="$HERE/bench/.claude/skills/earnings-orchestrator/scripts" \
KFIELDS_EVIDENCE="$EV" \
$PY - "$HERE" "$RUN" "$H" "$MODE" <<'PY'
import hashlib, io, json, os, shutil, sys
here, run, h, mode = sys.argv[1:5]
sys.path.insert(0, h); sys.path.insert(0, here)
import raw_transport as RT
import project_historical_tree as P
pkg_run = os.path.join(here, P.PACKAGE_RUN)
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

def expect(label, path, pkg_rel):
    """A generated file is lawful only when it equals its manifested package file."""
    want = os.path.join(here, pkg_rel)
    ok = os.path.isfile(want) and sha(path) == sha(want)
    print("%s %s %s" % (label, sha(path)[:16], "== package" if ok else "!= package %s" % pkg_rel))
    return ok

# ARM THE RUN EXACTLY AS THE GATE DID, in a fresh directory: writes the launchers and
# republishes a receipt
os.makedirs(run)
armed = RT.a1_prepare_run(run)
print("ARMED ok=%s problems=%s launchers=%d" % (armed.get("ok"), (armed.get("problems") or [])[:3], len(armed.get("launchers") or {})))
# the run's receipt AS THE RUN LEFT IT: the manifested bytes (19abb07c...)
shutil.copyfile(os.path.join(pkg_run, "receipt.json"), os.path.join(run, "receipt.json"))
out = RT.a1_finalize(run)
probs = list(out.get("problems") or [])
print("PRIMARY PROBLEMS %d %s" % (len(probs), [str(p)[:120] for p in probs[:3]]))
ok = expect("PRIMARY FINALIZATION", os.path.join(run, "finalization.json"), os.path.join(P.PACKAGE_RUN, "finalization.json"))
io.open(os.path.join(here, "evidence", "a3_finalization.rebuilt.json"), "wb").write(io.open(os.path.join(run, "finalization.json"), "rb").read())
# THE ONE LAWFUL RETRY
r = RT.a1_prepare_retry(run)
print("RETRY ARMED ok=%s problems=%s launchers=%d" % (r.get("ok"), (list(r.get("problems") or []))[:2], len(r.get("launchers") or {})))
child = os.path.join(run, "retry")
shutil.copyfile(os.path.join(pkg_run, "retry", "receipt.json"), os.path.join(child, "receipt.json"))
cout = RT.a1_finalize(child)
cprobs = list(cout.get("problems") or [])
print("RETRY PROBLEMS %d %s" % (len(cprobs), [str(p)[:120] for p in cprobs[:3]]))
ok2 = expect("RETRY FINALIZATION", os.path.join(child, "finalization.json"), os.path.join(P.PACKAGE_RUN, "retry", "finalization.json"))
io.open(os.path.join(here, "evidence", "a3_retry_finalization.rebuilt.json"), "wb").write(io.open(os.path.join(child, "finalization.json"), "rb").read())
# THE ARMED LAUNCHERS: vendored once, verified ever after
gen = []
for dp, _d, files in os.walk(run):
    for f in files:
        fp = os.path.join(dp, f)
        rel = os.path.relpath(fp, run)
        if rel not in ("receipt.json", "finalization.json", os.path.join("retry", "receipt.json"), os.path.join("retry", "finalization.json")):
            gen.append(rel)
# THE GATE IS THE IDENTITY. The primary finalization records the one audit problem
# that made the one lawful retry; that problem is part of the pinned bytes (92e1872c),
# so the finalizations equalling the package IS the proof, problems included.
if mode == "materialise":
    if not (ok and ok2):
        print("MATERIALISE REFUSED: the finalizations do not equal the package identities")
        raise SystemExit(5)
    for rel in gen:
        dst = os.path.join(pkg_run, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(run, rel), dst)
    print("MATERIALISED %d generated files into the package run directory" % len(gen))
else:
    missing = [rel for rel in gen if not os.path.isfile(os.path.join(pkg_run, rel)) or sha(os.path.join(run, rel)) != sha(os.path.join(pkg_run, rel))]
    print("GENERATED %d files; not package-backed: %d %s" % (len(gen), len(missing), missing[:3]))
    if missing: raise SystemExit(4)
# THE PINNED EVIDENCE OWNER ITSELF
kp = os.path.join(h, "build_kfields_key.py")
before = sha(kp)
import build_kfields_key as KEY
ev = KEY.a3_evidence()
after = sha(kp)
eprobs = list(ev.get("problems") or [])
print("BOUNDARY owner %s unchanged=%s answers %d problems %d" % (before[:16], after == before, len(ev.get("answers") or {}), len(eprobs)))
for p_ in eprobs[:5]: print("  BOUNDARY-PROBLEM", str(p_)[:160])
os.makedirs(os.path.join(here, "reports"), exist_ok=True)      # a clean checkout stages no report
io.open(os.path.join(here, "reports", "a3_evidence_boundary.json"), "w", encoding="utf-8").write(json.dumps({
    "owner": "build_kfields_key.py", "owner_sha256": before, "owner_unchanged_by_the_call": after == before,
    "callable": "a3_evidence", "answers": len(ev.get("answers") or {}), "problems": [str(x) for x in eprobs],
    "proved": not eprobs, "projected_from": "evidence/PROJECTION.tsv"}, indent=2) + "\n")
if mode != "materialise" and not (ok and ok2 and not eprobs and after == before):
    raise SystemExit(5)
PY
rc=$?
[ "$MODE" = "materialise" ] && exit $rc
[ $rc -eq 0 ] || { echo "NS: finalization refused rc=$rc"; exit $rc; }
# THE REAL NO-MODEL RESUME PATH with its explicit, verified inputs
cd "$HERE"
GUIDANCE_SCRIPTS_DIR="$HERE/bench/.claude/skills/earnings-orchestrator/scripts" \
$PY "$HERE/run_resume_path.py" --evidence-root "$EV" --projection "$HERE/evidence/PROJECTION.tsv"
rc=$?
# THE PROJECTED TREE AFTER THE RUN: still exactly the package, nothing else
$PY "$HERE/project_historical_tree.py" verify || exit 6
exit $rc
INNER
