# -*- coding: utf-8 -*-
"""The recovery wrappers' own failure paths (Codex SEQ 1741 item 3).

Only the wrappers this recovery added are covered - the historical owners are unchanged and
their evidence is reused. Every negative is taken at the real seam: the wrapper's own source
is parsed and the relevant statements are executed with stubbed inputs, or the wrapper is
run whole against an isolated copy. Nothing here touches the accepted candidate, the
bindings, the runs or any live evidence.

Classes covered, one owner per rule:
  valid control            - the stage filter keeps exactly the stages named
  wrong stage order        - the filter keeps the ORDER THEY WERE NAMED IN, not ORDER's
  missing required input   - the ledger gate refuses when its expected total is absent
  wrong required input     - the budget runner refuses a generator that is not the corrected one
  nonzero child            - the candidate wrapper refuses when the builder exits nonzero
  no executed pass / skip  - the test runner refuses a run that skipped or passed too few
  differing durable byte   - the run-dir seeder refuses rather than overwrite
  unknown owner            - the era-owner placer refuses a hash no proved owner has
"""
import ast
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
passed = failed = 0


def check(name, good, why=""):
    global passed, failed
    print("%-4s %-56s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)


def tail_of(path, first_line, last_line=None):
    """The wrapper's own statements in [first_line, last_line], from the real file."""
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    body = [n for n in tree.body if getattr(n, "lineno", 0) >= first_line
            and (last_line is None or getattr(n, "lineno", 0) <= last_line)]
    mod = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(mod)
    return compile(mod, path, "exec")


def run_code(code, ns):
    """-> (SystemExit code or None, printed text)"""
    buf, status = io.StringIO(), None
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, ns)
    except SystemExit as exc:
        status = exc.code
    return status, buf.getvalue()


# ---------------------------------------------------------------- the filter --
PIPE = UNIT + "/tests/a4_pipeline.py"
_tree = ast.parse(io.open(PIPE, encoding="utf-8").read())


def _assigns(name):
    return [n for n in _tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]


_order_node = _assigns("ORDER")[0]
_only_node = _assigns("only")[0]
_steps_node = _assigns("STEPS")[0]
#: the filter is every statement from `only` through the last one that builds STEPS
_filter_nodes = [n for n in _tree.body
                 if _only_node.lineno <= getattr(n, "lineno", 0)
                 <= max(_steps_node.lineno, getattr(_steps_node, "end_lineno", 0))]


def _module(nodes):
    m = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(m)
    return compile(m, PIPE, "exec")


def filter_with(steps):
    ns = {"os": types.SimpleNamespace(environ={"A4_STEPS": steps})}
    exec(_module([_order_node] + _filter_nodes), ns)
    return ns["STEPS"]


_ns = {}
exec(_module([_order_node]), _ns)
ORDER = _ns["ORDER"]
check("valid control: the filter keeps exactly the stages named",
      filter_with("bind_1509,ledger_check") == ["bind_1509", "ledger_check"],
      "%r" % (filter_with("bind_1509,ledger_check"),))
check("wrong stage order is impossible: the naming order is kept",
      filter_with("ledger_check,bind_1509") == ["ledger_check", "bind_1509"]
      and ORDER.index("ledger_check") < ORDER.index("bind_1509"),
      "named ledger_check first and ORDER agrees only by accident: %r"
      % (filter_with("ledger_check,bind_1509"),))
check("an unfiltered run is the whole order", filter_with("") == ORDER,
      "%d stages" % len(filter_with("")))
try:
    filter_with("bind_1509,not_a_stage")
    bad = False
except SystemExit as exc:
    bad = "not_a_stage" in str(exc)
check("a stage this pipeline does not have is refused", bad)

# ------------------------------------------------------- the ledger gate ------
r = subprocess.run([PY3, "-B", UNIT + "/reconstruct/ledger_check.py"], capture_output=True,
                   text=True, stdin=subprocess.DEVNULL,
                   env=dict((k, v) for k, v in os.environ.items() if k != "A4_LEDGER"))
check("missing required input: the ledger gate refuses with no expected total",
      r.returncode != 0 and "A4_LEDGER" in (r.stdout + r.stderr),
      "rc=%s %s" % (r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:]))

# ------------------------------------------------- the corrected budget runner -
BUD = UNIT + "/reconstruct/budget_receipt_1508.py"
blines = io.open(BUD, encoding="utf-8").read().splitlines()
bfirst = next(i for i, l in enumerate(blines, 1) if l.startswith("got = sha(GEN)"))
bcode = tail_of(BUD, bfirst, bfirst + 3)
for label, digest, want_refuse in (("the corrected generator", "WANT", False),
                                   ("a superseded generator", "2a436d27", True),
                                   ("an empty file", "", True)):
    ns = {"sha": lambda p, d=digest: ("WANT_VALUE" if d == "WANT" else d),
          "GEN": "/dev/null", "os": os, "sys": sys,
          "WANT_GEN": "WANT_VALUE"}
    status, _out = run_code(bcode, ns)
    check("wrong required input: budget runner on %s" % label,
          (status not in (None, 0)) == want_refuse, "status %r" % (status,))

# ------------------------------------------------------ the candidate wrapper --
CAND = UNIT + "/reconstruct/build_final_candidate.py"
clines = io.open(CAND, encoding="utf-8").read().splitlines()
cfirst = next(i for i, l in enumerate(clines, 1) if l.startswith("print((r.stdout"))
ccode = tail_of(CAND, cfirst, cfirst + 3)
for rc, want_refuse in ((0, False), (1, True), (2, True), (-9, True)):
    ns = {"r": types.SimpleNamespace(returncode=rc, stdout="", stderr="boom"),
          "sys": sys, "os": os}
    status, _out = run_code(ccode, ns)
    check("nonzero child: candidate wrapper on builder rc=%d" % rc,
          (status not in (None, 0)) == want_refuse, "status %r" % (status,))

# ----------------------------------------------------------- the test runner ---
CHK = UNIT + "/reconstruct/check_final_key_candidate.py"
klines = io.open(CHK, encoding="utf-8").read().splitlines()
kfirst = next(i for i, l in enumerate(klines, 1) if l.startswith("out = (r.stdout"))
kcode = tail_of(CHK, kfirst)
SEL = ("a", "b", "c", "d")
for label, rc, summary, want_refuse in (
        ("four executed passes", 0, "4 passed in 6.73s", False),
        ("a skip", 0, "3 passed, 1 skipped in 6.73s", True),
        ("all four passing but one skipped too", 0,
         "4 passed, 1 skipped in 6.73s", True),
        ("too few passes", 0, "2 passed in 1.00s", True),
        ("a failure", 1, "3 passed, 1 failed in 6.73s", True),
        ("nothing collected", 0, "no tests ran in 0.01s", True)):
    ns = {"r": types.SimpleNamespace(returncode=rc, stdout=summary + "\n", stderr=""),
          "re": __import__("re"), "sys": sys, "SELECTED": SEL, "print": print}
    status, _out = run_code(kcode, ns)
    check("no executed pass / skip: test runner on %s" % label,
          (status not in (None, 0)) == want_refuse, "status %r" % (status,))

# ------------------------------------------- the seeder and the owner placer ---
work = tempfile.mkdtemp(prefix="wrapper_iso_")
iso = os.path.join(work, "unit")
os.makedirs(os.path.join(iso, "tests"))
os.makedirs(os.path.join(iso, "out"))
os.makedirs(os.path.join(iso, "runs_rw", "a_run"))
shutil.copyfile(UNIT + "/tests/seed_runs_rw.py", os.path.join(iso, "tests", "seed_runs_rw.py"))
io.open(os.path.join(iso, "out", "a_run__receipt.json"), "w").write("{\"a\": 1}\n")
io.open(os.path.join(iso, "runs_rw", "a_run", "receipt.json"), "w").write("{\"a\": 2}\n")
r = subprocess.run([PY3, "-B", os.path.join(iso, "tests", "seed_runs_rw.py"), "a_run"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)
check("differing durable byte: the seeder refuses rather than overwrite",
      r.returncode != 0 and "REFUSE" in r.stdout,
      "rc=%s %s" % (r.returncode, r.stdout.strip().splitlines()[-1:]))
io.open(os.path.join(iso, "runs_rw", "a_run", "receipt.json"), "w").write("{\"a\": 1}\n")
r = subprocess.run([PY3, "-B", os.path.join(iso, "tests", "seed_runs_rw.py"), "a_run"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)
check("valid control: the seeder accepts the identical byte",
      r.returncode == 0 and "refused 0" in r.stdout, r.stdout.strip().splitlines()[-1:])

r = subprocess.run([PY3, "-B", UNIT + "/tests/place_era_owner.py",
                    "build_kfields_final_targeted.py", "0" * 64],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)
check("unknown owner: the placer refuses a hash no proved owner has",
      r.returncode != 0 and "REFUSE" in (r.stdout + r.stderr),
      (r.stdout + r.stderr).strip().splitlines()[-1:])
r = subprocess.run([PY3, "-B", UNIT + "/tests/place_era_owner.py",
                    "not_a_bench_file.py", "0" * 64],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)
check("unknown file: the placer refuses a name the bench does not carry",
      r.returncode != 0 and "REFUSE" in (r.stdout + r.stderr),
      (r.stdout + r.stderr).strip().splitlines()[-1:])
shutil.rmtree(work, ignore_errors=True)

print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
