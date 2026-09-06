# -*- coding: utf-8 -*-
"""The freeze's own refusal gates (Codex SEQ 1742 item 2).

The first freeze recorded a failed test as executed and went on to declare success. That
defect is shown here on its PRESERVED source - the same bytes Codex read - and then each
gate of the corrected freeze is exercised with a real valid control and isolated inputs.
Nothing here writes a freeze or touches any accepted output.
"""
import ast
import io
import os
import sys
import types

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = UNIT + "/superseded/FREEZE_1741/freeze_1741.py"
NEW = UNIT + "/tests/freeze_1742.py"
passed = failed = 0


def check(name, good, why=""):
    global passed, failed
    print("%-4s %-56s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)


# --- the defect, on the preserved source of the first freeze -------------------
old_src = io.open(OLD, encoding="utf-8").read()
old_tree = ast.parse(old_src)
loops = [n for n in ast.walk(old_tree) if isinstance(n, ast.For)
         and "LOCAL_TESTS" in ast.dump(n.iter)]
check("the first freeze's test loop is found", len(loops) == 1, "%d loop(s)" % len(loops))
guarded = any(isinstance(n, ast.If) and "returncode" in ast.dump(n.test)
              for n in ast.walk(loops[0])) if loops else True
check("the first freeze never checked a test's return code", not guarded,
      "no returncode guard inside the loop")
check("and nothing refused before it declared success",
      "FREEZE_OK" in old_src and "sys.exit" not in old_src.split("FREEZE_OK")[0][-400:],
      "the success line follows the loop unguarded")

# --- the corrected gates -------------------------------------------------------
mod = types.ModuleType("freeze_1742")
mod.__file__ = NEW
tree = ast.parse(io.open(NEW, encoding="utf-8").read())
#: only the definitions - main() is not run here
defs = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign,
                                               ast.FunctionDef))]
m = ast.Module(body=defs, type_ignores=[])
ast.fix_missing_locations(m)
exec(compile(m, NEW, "exec"), mod.__dict__)

check("valid control: all tests passed", mod.gate_tests(
    [("a", 0, "/dev/null"), ("b", 0, "/dev/null")]) == [], "no problems")
for rc in (1, 2, 127, -9):
    check("a required test with rc=%d refuses" % rc,
          bool(mod.gate_tests([("a", 0, "x"), ("b", rc, "x")])),
          mod.gate_tests([("a", 0, "x"), ("b", rc, "x")])[:1])

check("valid control: the unchanged-input checks hold",
      mod.gate_unchanged([("prior", "rows 109 mismatched 0 extra 0",
                           "rows 109 mismatched 0 extra 0")]) == [], "no problems")
for got in ("rows 109 mismatched 1 extra 0", "", "rows 108 mismatched 0 extra 0"):
    check("an unchanged-input check reading %r refuses" % (got[:28] or "empty"),
          bool(mod.gate_unchanged([("prior", "rows 109 mismatched 0 extra 0", got)])))

real_log = "logs/" + sorted(f for f in os.listdir(UNIT + "/logs") if f.startswith("a4_"))[-1]
good_row = {"kind": "executed", "what": "x", "log": real_log,
            "log_sha256": mod.sha(os.path.join(UNIT, real_log))}
check("valid control: an evidence row that binds", mod.gate_evidence([good_row]) == [],
      real_log)
for label, row in (("no log", dict(good_row, log="")),
                   ("a log that is not there", dict(good_row, log="logs/nope.log")),
                   ("a wrong hash", dict(good_row, log_sha256="0" * 64))):
    check("an evidence row with %s refuses" % label, bool(mod.gate_evidence([row])),
          mod.gate_evidence([row])[:1])
check("a reused row is not required to carry a log",
      mod.gate_evidence([{"kind": "reused", "what": "y"}]) == [])

req = [mod.R + "/a/b/c.py", mod.R + "/d/e.py"]
check("valid control: every required input is covered",
      mod.gate_coverage(req, ["a/b"], {"d/e.py"}) == [], "one root, one tracked file")
check("an uncovered required input refuses",
      bool(mod.gate_coverage(req, ["a/b"], set())),
      mod.gate_coverage(req, ["a/b"], set())[:1])
check("a root that only looks like a prefix does not cover",
      bool(mod.gate_coverage([mod.R + "/a/bc.py"], ["a/b"], set())))

print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
