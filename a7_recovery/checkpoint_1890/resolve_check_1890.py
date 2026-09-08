# -*- coding: utf-8 -*-
"""Codex SEQ 1890 item D: resolve the grading entrypoints against HEAD+index.

The populated working directory hides omissions, so every read of a path inside
the recovery tree is answered from the INDEX (which is HEAD plus what is
staged). A file that is not staged and not committed is MISSING here even
though it exists on disk. A symlink resolves only if its own entry is in the
index AND its target is too.

Read-only: it opens files, it never writes one. No model call.
"""
import builtins, collections, io, json, os, subprocess, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
V = R + "/a7_recovery/unit_1881/view/tree/harness_g1v3"
OUT = os.path.dirname(os.path.abspath(__file__))

index = set(subprocess.run(["git", "-C", R, "ls-files"],
                           capture_output=True, text=True).stdout.splitlines())
DROP = set(sys.argv[1:])          # negative control: pretend these are absent
index -= DROP

_real_open = builtins.open
_real_isfile = os.path.isfile
_real_exists = os.path.exists
_real_isdir = os.path.isdir
denied = collections.Counter()


def _known(path):
    """True when this path is answerable from HEAD+index."""
    try:
        ap = os.path.abspath(path)
    except Exception:
        return True
    if not ap.startswith(R + os.sep):
        return True                       # outside the tree: not our gate
    rel = os.path.relpath(ap, R)
    if rel in index:
        return True
    if any(p.startswith(rel + "/") for p in index):
        return True                       # a directory the index populates
    real = os.path.realpath(ap)
    if real.startswith(R + os.sep):
        rrel = os.path.relpath(real, R)
        if rrel in index or any(p.startswith(rrel + "/") for p in index):
            # the target is committed, but the LINK itself must be too
            return rel in index or any(p.startswith(rel + "/") for p in index)
    denied[rel] += 1
    return False


def gated_open(file, *a, **k):
    if isinstance(file, str) and not _known(file):
        raise FileNotFoundError(2, "not in HEAD+index", file)
    return _real_open(file, *a, **k)


builtins.open = gated_open
io.open = gated_open
os.path.isfile = lambda p: _known(p) and _real_isfile(p)
os.path.exists = lambda p: _known(p) and _real_exists(p)
os.path.isdir = lambda p: _known(p) and _real_isdir(p)

sys.path.insert(0, R)
sys.path.insert(0, V)

res = collections.OrderedDict(dropped_for_this_run=sorted(DROP))
steps = collections.OrderedDict()


def step(name, fn):
    try:
        fn()
        steps[name] = "ok"
    except Exception as exc:
        steps[name] = "%s: %s" % (type(exc).__name__, str(exc)[:160])


import raw_transport as RT                                       # noqa: E402
import a7_g1_build as G                                          # noqa: E402

step("raw_transport.a1_plan_path", lambda: RT.a1_plan_path())
step("raw_transport.a1_plan", lambda: RT.a1_plan())
step("a7_g1_build.owner_hashes", lambda: G.owner_hashes())
step("import build_kfields_key", lambda: __import__("build_kfields_key"))
step("import a7_g23_build", lambda: __import__("a7_g23_build"))
step("import a7_g23_run", lambda: __import__("a7_g23_run"))
step("import a7_g1_complete_v2", lambda: __import__("a7_g1_complete_v2"))
step("import audit_worker_access", lambda: __import__("audit_worker_access"))
step("import scorers.score_exp5_current",
     lambda: __import__("scorers.score_exp5_current"))
step("import validate_benchmark_inventory",
     lambda: __import__("validate_benchmark_inventory"))


def _read_inventory_through_its_link():
    """The inventory is reached by a SYMLINK; a committed target alone does
    not recreate the link, so this step must fail if the link is unstaged."""
    import validate_benchmark_inventory as INV
    import json as _j
    with open(INV.INV) as fh:
        doc = _j.load(fh)
    assert doc["records"], "the inventory carries no records"


step("read the inventory through its link", _read_inventory_through_its_link)

res["steps"] = steps
res["denied_paths"] = dict(denied)
res["all_ok"] = all(v == "ok" for v in steps.values())
builtins.open, io.open = _real_open, _real_open
os.path.isfile, os.path.exists, os.path.isdir = (_real_isfile, _real_exists,
                                                 _real_isdir)
name = "RESOLVE_NEGATIVE.json" if DROP else "RESOLVE_POSITIVE.json"
_real_open(os.path.join(OUT, name), "w").write(
    json.dumps(res, indent=1, default=str))
print("all_ok:", res["all_ok"], " dropped:", sorted(DROP) or "none")
for k, v in steps.items():
    print("  %-38s %s" % (k, v if v == "ok" else v[:110]))
if denied:
    print("denied (not in HEAD+index):")
    for p, n in sorted(denied.items()):
        print("   %-70s x%d" % (p, n))
sys.exit(0 if res["all_ok"] else 1)
