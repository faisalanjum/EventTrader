# -*- coding: utf-8 -*-
"""RED executable test (Codex SEQ 1695 item 1).

Demonstrates that the current unit CANNOT complete the real
`FT._baseline()` / `FT.primary_shards()` runtime path, and derives the direct
dependency inventory BY EXECUTING THE REAL OWNERS - not by hand and not by
import inspection.

It runs inside the private namespace payload slot. Every filesystem question the
owners ask is recorded through the real answer, so a path that is merely CHECKED
and found absent is captured too; that is where the missing direct dependencies
show up. The first failing checkpoint is reported exactly.

Exit 1 = RED (the path cannot complete). Exit 0 would mean the gap is closed.
"""
import builtins
import io
import json
import os
import sys
import traceback

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT = os.environ["RED_TRACE"]          # durable unit/manifest path to write

sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

# ---- trace every filesystem question the real owners ask -------------------
REQ = []                                # (kind, abspath, existed)
_open, _ioopen = builtins.open, io.open
_isfile, _isdir, _exists, _listdir = (os.path.isfile, os.path.isdir,
                                      os.path.exists, os.listdir)


def _rec(kind, p, ok):
    if not isinstance(p, str):
        return
    try:
        REQ.append((kind, os.path.abspath(p), bool(ok)))
    except Exception:
        pass


def w_open(*a, **k):
    if a:
        _rec("open", a[0], _exists(a[0]) if isinstance(a[0], str) else True)
    return _open(*a, **k)


def w_ioopen(*a, **k):
    if a:
        _rec("open", a[0], _exists(a[0]) if isinstance(a[0], str) else True)
    return _ioopen(*a, **k)


def w_isfile(p):
    r = _isfile(p); _rec("isfile", p, r); return r


def w_isdir(p):
    r = _isdir(p); _rec("isdir", p, r); return r


def w_exists(p):
    r = _exists(p); _rec("exists", p, r); return r


def w_listdir(p="."):
    try:
        r = _listdir(p); _rec("listdir", p, True); return r
    except OSError:
        _rec("listdir", p, False); raise


builtins.open, io.open = w_open, w_ioopen
os.path.isfile, os.path.isdir, os.path.exists = w_isfile, w_isdir, w_exists
os.listdir = w_listdir

import build_kfields_final_targeted as FT                       # noqa: E402

# ---- run the real checkpoints, in Codex's order ---------------------------
checkpoints = []
first_gap = None


def attempt(name, fn):
    """Execute one real owner entry point; record the exact outcome."""
    global first_gap
    try:
        fn()
        checkpoints.append((name, "ok", ""))
    except BaseException as exc:                     # noqa: BLE001 - recorded, never hidden
        detail = "%s: %s" % (type(exc).__name__, str(exc)[:400])
        checkpoints.append((name, "FAILED", detail))
        if first_gap is None:
            first_gap = (name, detail, traceback.format_exc()[-2000:])


attempt("FT._baseline (-> A6.bound -> F.v6_shards, pre-targeted signed history)",
        lambda: FT._baseline())
attempt("FT.primary_shards", lambda: FT.primary_shards())

# ---- restore the real functions before writing anything -------------------
builtins.open, io.open = _open, _ioopen
os.path.isfile, os.path.isdir, os.path.exists = _isfile, _isdir, _exists
os.listdir = _listdir

# ---- derive the dependency inventory from what actually happened ----------
seen, missing, present = set(), [], []
for kind, path, ok in REQ:
    key = (kind, path)
    if key in seen:
        continue
    seen.add(key)
    (present if ok else missing).append((kind, path))

# only project paths matter; the venv/stdlib are not recovery inputs
def _project(p):
    return (p.startswith(S)
            or p.startswith("/home/faisal/EventMarketDB-driver-recovery")
            or p.startswith("/home/faisal/EventMarketDB/")
            or p.startswith("/home/faisal/.claude/projects"))


missing = [(k, p) for k, p in missing if _project(p)]
present = [(k, p) for k, p in present if _project(p)]

report = {
    "checkpoints": [{"name": n, "status": s, "detail": d} for n, s, d in checkpoints],
    "first_gap": ({"checkpoint": first_gap[0], "error": first_gap[1],
                   "traceback_tail": first_gap[2]} if first_gap else None),
    "counts": {"distinct_requested": len(seen),
               "project_missing": len(missing),
               "project_present": len(present)},
    "missing_project_paths": [{"kind": k, "path": p.replace(S, "S")} for k, p in missing],
    "present_project_paths": [{"kind": k, "path": p.replace(S, "S")} for k, p in present],
}
with _open(OUT, "w") as fh:
    json.dump(report, fh, indent=1)
    fh.write("\n")

print("CHECKPOINTS:")
for n, s, d in checkpoints:
    print("  [%s] %s%s" % (s, n, ("  <- " + d) if d else ""))
print("distinct filesystem questions: %d | project MISSING: %d | project present: %d"
      % (len(seen), len(missing), len(present)))
if first_gap:
    print("FIRST GAP at checkpoint: %s" % first_gap[0])
    print("  error: %s" % first_gap[1])
print("first missing project paths (up to 25):")
for k, p in missing[:25]:
    print("   %-8s %s" % (k, p.replace(S, "S")))
print("RED" if first_gap else "GREEN")
sys.exit(1 if first_gap else 0)
