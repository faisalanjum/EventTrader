# -*- coding: utf-8 -*-
"""The per-owner extraction must emit each selected statement ONCE (Codex SEQ 1726).

RED FIRST: the real record is the case that failed. Three of its top-level statements
share one physical line, and the old extractor appended that whole line once per
statement and joined the pieces with nothing, so the fragment read
`print(...)io.open(...)` and did not parse. The controls beside it are the properties
that failure exposed - a statement sharing a line must not drag its neighbours in, the
last line may carry no newline - plus the rule this seam exists for: another owner's
statements stay out even when they share a line with mine.

The audit is over the recorded extractions this recovery actually performs, not over
arbitrary Python: every record in the walk must yield a fragment that parses.

Run: python3 -B tests/test_extraction_1726.py
"""
import ast
import io
import json
import os
import re
import sys

A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, A)
import recover_a4_owner as C                                    # noqa: E402

RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
RECORD, TOOL_ID, OWNER = 73642, "toolu_01V6edf4KmV4pw7ThYADi1Nd", "a7_g23_build.py"
OTHER = "a7_reference_inventory.py"
LINES = io.open(RAW, encoding="utf-8", errors="replace").readlines()
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok)))
    print("%s %s%s" % ("ok  " if ok else "BAD ", name, "" if ok else "   <- %s" % str(detail)[:220]))


def parses(src):
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        return exc


def command_of(n):
    for c in (json.loads(LINES[n - 1]).get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            return (c.get("input") or {}).get("command", ""), c.get("id")
    return "", ""


def programs(cmd):
    return [b for _t, b in re.findall(r"<<'?([A-Za-z0-9_]+)'?[^\n]*\n(.*?)\n\1\s*$",
                                      cmd, re.S | re.M)]


# ---- 1. the real record ------------------------------------------------------
cmd, tid = command_of(RECORD)
check("the record is the one the reviewer named", tid == TOOL_ID, tid)
progs = programs(cmd)
check("the record carries exactly one program", len(progs) == 1, len(progs))
src = progs[0]
check("the ORIGINAL program parses", parses(src) is True, parses(src))
kept, _w = C.blocks_for(src, OWNER)
check("the EXTRACTED fragment parses", parses(kept) is True, parses(kept))
check("the fragment does not run two statements together",
      not re.search(r"\)\s*io\.open\(", kept.replace(")\nio.open(", ")NL")),
      [l for l in kept.splitlines() if re.search(r"\)io\.open\(", l)][:1])

# ---- 1b. the failure is still reproducible, against the UNFIXED accepted caller ----
# The accepted unit keeps the extractor as it was, so the RED is not a memory of a run
# that has since been edited away: it can be re-observed at any time.
import importlib.util                                            # noqa: E402
_old = importlib.util.spec_from_file_location(
    "accepted_caller",
    P_ACCEPTED := os.path.dirname(A) + "/budget_inputs_1720/recover_g23_sources.py")
_m = importlib.util.module_from_spec(_old)
_old.loader.exec_module(_m)
_kept_old, _ = _m.blocks_for(src, OWNER)
check("the UNFIXED extractor still fails on this record",
      parses(_kept_old) is not True, "it parsed, so the RED is gone")

# ---- 2. the properties that failure exposed, in the record's own shape --------
SAME_LINE = ('import io\n'
             'p = "%s"; s = io.open(p).read(); io.open(p, "w").write(s + "x")\n'
             'q = "%s"; t = io.open(q).read(); io.open(q, "w").write(t + "y")\n'
             % (OWNER, OTHER))
kept, writes = C.blocks_for(SAME_LINE, OWNER)
check("same-line statements: the fragment parses", parses(kept) is True, parses(kept))
check("same-line statements: mine is emitted exactly once",
      kept.count('io.open(p, "w")') == 1, kept.count('io.open(p, "w")'))
check("same-line statements: the other owner is excluded",
      OTHER not in kept and 'io.open(q, "w")' not in kept, kept)
check("same-line statements: the write is still recognised", writes is True, writes)

NO_NEWLINE = 'import io\np = "%s"\nio.open(p, "w").write("z")' % OWNER
kept, writes = C.blocks_for(NO_NEWLINE, OWNER)
check("a program with no final newline: the fragment parses", parses(kept) is True, parses(kept))
check("a program with no final newline: the write is recognised", writes is True, writes)

ONLY_OTHER = 'import io\nq = "%s"\nio.open(q, "w").write("z")' % OTHER
kept, writes = C.blocks_for(ONLY_OTHER, OWNER)
check("another owner alone: nothing of it is kept", OTHER not in kept, kept)
check("another owner alone: no write is claimed for mine", writes is False, writes)

# ---- 3. audit: every recorded extraction this recovery performs ---------------
bad = []
for n in range(1, 84829):
    if OWNER not in LINES[n - 1]:
        continue
    cmd, _t = command_of(n)
    if not cmd:
        continue
    for s in programs(cmd):
        k, _w = C.blocks_for(s, OWNER)
        if parses(s) is True and parses(k) is not True:
            bad.append(n)
            break
check("every recorded extraction in the walk parses when the program did",
      not bad, "records %s" % bad[:6])

n_bad = [c for c, ok in checks if not ok]
print("checks: %d  failed: %d  %s" % (len(checks), len(n_bad), n_bad[:4]))
sys.exit(1 if n_bad else 0)
