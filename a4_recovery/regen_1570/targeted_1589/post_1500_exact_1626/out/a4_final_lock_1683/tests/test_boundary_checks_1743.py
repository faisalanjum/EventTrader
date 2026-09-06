# -*- coding: utf-8 -*-
"""The checks Codex SEQ 1743 item 4 found accepting what they should refuse.

Each case is run at the real owner - the freeze's own gate functions taken out of the
freeze source, and the prior-unit verifier run as itself over an ISOLATED COPY of the
accepted unit (the accepted unit is never touched). Valid controls first, then the actual
failures that used to pass.
"""
import ast
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.dirname(os.path.dirname(UNIT))
A = P + "/a4_owner_1726"
PRIOR = P + "/budget_inputs_1720"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
FREEZE = UNIT + "/tests/freeze_1743.py"
passed = failed = 0


def check(name, good, why=""):
    global passed, failed
    print("%-4s %-58s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)


mod = types.ModuleType("freeze_1743")
mod.__file__ = FREEZE
tree = ast.parse(io.open(FREEZE, encoding="utf-8").read())
defs = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign,
                                               ast.FunctionDef))]
m = ast.Module(body=defs, type_ignores=[])
ast.fix_missing_locations(m)
exec(compile(m, FREEZE, "exec"), mod.__dict__)

# --- the evidence gate must check the marker and the run IN the log ---------------
log = "logs/" + sorted(f for f in os.listdir(UNIT + "/logs") if f.startswith("a4_"))[-1]
text = io.open(os.path.join(UNIT, log), encoding="utf-8", errors="replace").read()
marker = "CHECKPOINT_OK" if "CHECKPOINT_OK" in text else text.strip().splitlines()[0][:12]
run = "verify problems" if "verify problems" in text else marker
good = {"kind": "executed", "what": "control", "log": log,
        "log_sha256": mod.sha(os.path.join(UNIT, log)), "marker": marker, "run": run}
check("valid control: a row whose marker and run are in its log",
      mod.gate_evidence([good]) == [], log)
for label, row in (("an invented marker", dict(good, marker="NEVER_PRINTED_MARKER")),
                   ("a run that is not in the log", dict(good, run="a4_never_run_9999")),
                   ("a wrong log hash", dict(good, log_sha256="0" * 64)),
                   ("no log at all", dict(good, log=""))):
    check("the evidence gate refuses %s" % label, bool(mod.gate_evidence([row])),
          mod.gate_evidence([row])[:1])

# --- the unchanged gate must look at the return code ------------------------------
ok_line = "rows 109 mismatched 0 extra 0 missing 0"
check("valid control: the unchanged check passed",
      mod.gate_unchanged([("prior", ok_line, ok_line, 0)]) == [])
check("the unchanged gate refuses a nonzero return code even with the right text",
      bool(mod.gate_unchanged([("prior", ok_line, ok_line, 13)])),
      mod.gate_unchanged([("prior", ok_line, ok_line, 13)])[:1])
check("the unchanged gate refuses different text",
      bool(mod.gate_unchanged([("prior", ok_line, "rows 108 mismatched 1 extra 0 missing 0", 0)])))

# --- the coverage gate must refuse an absent required file ------------------------
work = tempfile.mkdtemp(prefix="cov_")
real = os.path.join(work, "a", "b", "there.py")
os.makedirs(os.path.dirname(real))
io.open(real, "w").write("x\n")
R = mod.R
check("valid control: a required file that exists under a root",
      mod.gate_coverage([real], [os.path.relpath(os.path.dirname(real), R)], set(), set()) == [],
      "covered by its directory root")
check("the coverage gate refuses a file that does not exist",
      bool(mod.gate_coverage([os.path.join(work, "a", "b", "gone.py")],
                             [os.path.relpath(os.path.dirname(real), R)], set(), set())),
      mod.gate_coverage([os.path.join(work, "a", "b", "gone.py")],
                        [os.path.relpath(os.path.dirname(real), R)], set(), set())[:1])
shutil.rmtree(work, ignore_errors=True)

# --- the prior-unit verifier must notice a DELETED listed file --------------------
iso = tempfile.mkdtemp(prefix="prior_")
dst = os.path.join(iso, "budget_inputs_1720")
shutil.copytree(PRIOR, dst, symlinks=True,
                ignore=shutil.ignore_patterns("bench", "bench_g23", "__pycache__"))
env = dict(os.environ, PRIOR_UNIT=dst, PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([PY3, "-B", A + "/verify_prior_unit.py"], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, env=env, timeout=900)
check("valid control: the isolated copy verifies", r.returncode == 0 and "missing 0" in r.stdout,
      r.stdout.strip().splitlines()[:1])
listed = [l.split("\t")[0] for l in
          io.open(dst + "/MANIFEST_g23.sha256", encoding="utf-8").read().splitlines()[1:]]
victim = os.path.join(dst, listed[0])
os.remove(victim)
r = subprocess.run([PY3, "-B", A + "/verify_prior_unit.py"], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, env=env, timeout=900)
check("the verifier refuses when a listed file was deleted",
      r.returncode != 0 and "missing 1" in r.stdout, r.stdout.strip().splitlines()[:1])
shutil.rmtree(iso, ignore_errors=True)

# --- the harvest wrapper's own nonzero-child seam ---------------------------------
H = UNIT + "/reconstruct/harvest_final_sign_run.py"
hlines = io.open(H, encoding="utf-8").read().splitlines()
hfirst = next(i for i, l in enumerate(hlines, 1) if l.startswith("print((r.stdout"))
htree = ast.parse(io.open(H, encoding="utf-8").read())
tail = [n for n in htree.body if getattr(n, "lineno", 0) >= hfirst]
hmod = ast.Module(body=tail, type_ignores=[])
ast.fix_missing_locations(hmod)
hcode = compile(hmod, H, "exec")
for rc, want_refuse in ((0, False), (2, True), (3, True), (4, True)):
    ns = {"r": types.SimpleNamespace(returncode=rc, stdout="", stderr="x"), "sys": sys}
    status = None
    try:
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            exec(hcode, ns)
    except SystemExit as exc:
        status = exc.code
    check("the harvest wrapper on harvester rc=%d" % rc,
          (status not in (None, 0)) == want_refuse, "status %r" % (status,))

print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
