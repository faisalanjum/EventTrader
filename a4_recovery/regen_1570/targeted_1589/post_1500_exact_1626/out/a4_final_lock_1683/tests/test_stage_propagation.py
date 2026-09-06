# -*- coding: utf-8 -*-
"""A failed stage stops the pipeline (Codex SEQ 1741 item 1, last sentence).

Two independent proofs, no new run of anything expensive:

  SOURCE - the runner's own loop must leave the loop on a nonzero child and the run must
  end nonzero. Read out of the real a4_pipeline.py by AST, not by eye.

  EXECUTED - every run log this unit already produced that carries a failed stage must
  show that stage LAST, name it in the refusal line, and carry no later stage. These are
  real failures from today's runs, so the propagation is observed, not assumed.
"""
import ast
import io
import os
import re
import sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = UNIT + "/tests/a4_pipeline.py"
LOGS = UNIT + "/logs"
STAGE = re.compile(r"^(ok|BAD)\s+(\S+)\s+rc=(-?\d+)", re.M)

passed = failed = 0


def check(name, good, why=""):
    global passed, failed
    print("%-4s %-52s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)


tree = ast.parse(io.open(SRC, encoding="utf-8").read())
loop = [n for n in ast.walk(tree)
        if isinstance(n, ast.For) and any(isinstance(b, ast.Break) for b in ast.walk(n))]
check("the runner leaves its stage loop on a failure", bool(loop),
      "%d loop(s) with a break" % len(loop))
breaks = [n for n in ast.walk(loop[0]) if isinstance(n, ast.Break)] if loop else []
guards = [n for n in ast.walk(loop[0])
          if isinstance(n, ast.If) and any(isinstance(b, ast.Break) for b in ast.walk(n))] if loop else []
check("the break is guarded by the child's return code",
      bool(guards) and "returncode" in ast.dump(guards[0].test),
      "guard test %s" % (ast.dump(guards[0].test)[:60] if guards else "none"))
src = io.open(SRC, encoding="utf-8").read()
check("a failed run ends nonzero", "sys.exit(2)" in src or "raise SystemExit(2)" in src,
      "the runner exits 2 on a failed stage")

logs = sorted(f for f in os.listdir(LOGS) if f.startswith("a4_") and f.endswith(".log"))
observed = 0
multi = []
for f in logs:
    text = io.open(os.path.join(LOGS, f), encoding="utf-8", errors="replace").read()
    stages = [(m.group(1).strip(), m.group(2)) for m in STAGE.finditer(text)]
    bad = [i for i, (k, _n) in enumerate(stages) if k == "BAD"]
    if not bad:
        continue
    observed += 1
    i, name = bad[0], stages[bad[0]][1]
    check("%s: the failed stage is the last one" % f, i == len(stages) - 1,
          "%d stage lines, failure at %d (%s)" % (len(stages), i, name))
    check("%s: the refusal names it" % f, ("REFUSED: step %s failed" % name) in text,
          "REFUSED: step %s failed" % name)
    if len(stages) > 1:
        multi.append((f, len(stages), name))

check("a multi-stage run stopped at its failure", bool(multi),
      "; ".join("%s %d stages, failed at %s" % m for m in multi) or "none")
check("failed runs were actually observed", observed > 0, "%d logs carry a failed stage" % observed)
print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
