# -*- coding: utf-8 -*-
"""A command that edits this file AND writes it must do both (Codex SEQ 1728).

Record 66620 runs five replacements against a7_g23_build.py and then appends to the same
file with the shell. The caller used to see the append, label the record a file write and
skip the program entirely, so five completed edits vanished while the row still looked
successful.

The expected bytes are DERIVED here from the record itself - the five (old, new) pairs
are read out of the program's own syntax tree and the appended text out of its own
heredoc - and applied to the durable base the chain reaches just before it. The recorded
identity is then a check on that derivation, never its input.

Run: python3 -B tests/test_mixed_command_1728.py
"""
import ast
import hashlib
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
OWNER = "a7_g23_build.py"
RECORD, TOOL_ID, RESULT = 66620, "toolu_013zXxmazysBhDsuKvUYpQrp", 66626
BASE_PIN = "97e0e2f1ce73209fcb101366dde4f9786a70ec9a13c782d6e0fe41b0322c7658"
WANT = "4f44aaf85267cdc68acfd3ed63c33207f6312a54e18e72458e9d874fbb07fae8"
WANT_BYTES = 20284
#: the base is found BY ITS HASH, so replacing a bench copy cannot move what this
#: test measures against
BASE = C.durable(BASE_PIN)
OPS = A + "/sources_a4/SOURCE_OPS.tsv"
L = io.open(RAW, encoding="utf-8", errors="replace").readlines()
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok)))
    print("%s %s%s" % ("ok  " if ok else "BAD ", name, "" if ok else "   <- %s" % str(detail)[:200]))


cmd = tid = None
for c in (json.loads(L[RECORD - 1]).get("message") or {}).get("content") or []:
    if isinstance(c, dict) and c.get("type") == "tool_use":
        cmd, tid = (c.get("input") or {}).get("command", ""), c.get("id")
ok_res = False
for m in range(RECORD, len(L)):
    if tid and tid in L[m]:
        for c in (json.loads(L[m]).get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_result" \
                    and c.get("tool_use_id") == tid:
                ok_res = (m + 1 == RESULT) and not c.get("is_error")
        break
check("66620 is the record the reviewer named, with its successful result",
      tid == TOOL_ID and ok_res, (tid, ok_res))

check("the command's program runs BEFORE its write to this file",
      C.prog_before_write(cmd, OWNER) is True, C.prog_before_write(cmd, OWNER))

# the five substitutions, read out of the program's own tree
prog = [b for _t, b in re.findall(r"<<'?([A-Za-z0-9_]+)'?[^\n]*\n(.*?)\n\1\s*$",
                                  cmd, re.S | re.M)
        if "s = s.replace" in b]
check("the record carries exactly one edit program", len(prog) == 1, len(prog))
pairs = []
for node in ast.walk(ast.parse(prog[0])):
    if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "replace" \
            and len(node.args) == 2 \
            and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in node.args):
        pairs.append((node.args[0].value, node.args[1].value))
check("the program states five replacements", len(pairs) == 5, len(pairs))

# the appended text, out of its own heredoc
app = [b for op, p_, _t, b in C.HD.findall(cmd) if p_.strip("\"'").endswith(OWNER) and op == ">>"]
check("the command appends to this file exactly once", len(app) == 1, len(app))

base = io.open(BASE, encoding="utf-8").read()
check("the base is the proven earlier state",
      hashlib.sha256(base.encode()).hexdigest() == BASE_PIN,
      hashlib.sha256(base.encode()).hexdigest()[:16])
counts = [base.count(o) for o, _n in pairs]
check("each old anchor occurs exactly once in that base", counts == [1] * 5, counts)

got = base
for o, nw in pairs:
    got = got.replace(o, nw)
got = got + app[0] + "\n"
check("program then append reproduces the recorded identity",
      hashlib.sha256(got.encode()).hexdigest() == WANT and len(got.encode()) == WANT_BYTES,
      (hashlib.sha256(got.encode()).hexdigest()[:16], len(got.encode())))

# and the chain must actually contain it
row = [l.split("\t") for l in io.open(OPS, encoding="utf-8").read().splitlines()[1:]
       if l.split("\t")[1] == str(RECORD)]
check("the recovery table records 66620", len(row) == 1, len(row))
if row:
    check("the chain's own state after 66620 is that identity",
          row[0][7] == WANT and row[0][8] == str(WANT_BYTES), (row[0][7][:16], row[0][8]))

bad = [n for n, ok in checks if not ok]
print("checks: %d  failed: %d  %s" % (len(checks), len(bad), bad[:3]))
sys.exit(1 if bad else 0)
