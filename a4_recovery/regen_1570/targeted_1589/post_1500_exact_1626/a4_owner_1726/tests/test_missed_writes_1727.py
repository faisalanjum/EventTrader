# -*- coding: utf-8 -*-
"""The two write forms this recovery silently dropped (Codex SEQ 1727).

Both are real records with successful results, tested against those originals:

  70321  rewires the same call in two owners with `for f in ("a", "b")`. The loop was
         dropped whole, so the file was never written and no row was recorded at all.
         The reviewer's independent application of that one substitution to the
         accepted earlier state is required here as the exact result.
  75912  makes three writes through an `edit(path, old, new, why)` helper it defines,
         after one call for ANOTHER owner. The record was recorded as read-only, so the
         three completed edits were lost - and the other owner's call must still be
         excluded.

Run: python3 -B tests/test_missed_writes_1727.py
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
OWNER, OTHER = "a7_g23_build.py", "a7_g1_build.py"
ACCEPTED = (os.path.dirname(A) + "/budget_inputs_1720/sources_g23/a7_g23_build.py")
#: the reviewer's independent result of applying 70321's one substitution to that state
WANT_70321 = "804d02b680835af8e746df2e4ffedea5ee771b20fff4e6e8cd063f824e196068"
LINES = io.open(RAW, encoding="utf-8", errors="replace").readlines()
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok)))
    print("%s %s%s" % ("ok  " if ok else "BAD ", name, "" if ok else "   <- %s" % str(detail)[:220]))


def use(n):
    for c in (json.loads(LINES[n - 1]).get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            return (c.get("input") or {}).get("command", ""), c.get("id")
    return "", ""


def result_of(n, tid):
    for m in range(n, len(LINES)):
        if tid not in LINES[m]:
            continue
        for c in (json.loads(LINES[m]).get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_result" \
                    and c.get("tool_use_id") == tid:
                x = c.get("content")
                if isinstance(x, list):
                    x = "".join(i.get("text", "") for i in x if isinstance(i, dict))
                return m + 1, x, bool(c.get("is_error"))
    return 0, "", True


def program(cmd):
    b = re.findall(r"<<'?([A-Za-z0-9_]+)'?[^\n]*\n(.*?)\n\1\s*$", cmd, re.S | re.M)
    return b[0][1] if len(b) == 1 else None


# ---- 70321: the literal loop --------------------------------------------------
cmd, tid = use(70321)
rl, res, err = result_of(70321, tid)
check("70321 is the record the reviewer named",
      tid == "toolu_01EFJpVwKS7ZjFbygViq52Ha" and rl == 70327 and not err, (tid, rl, err))
check("its own result reports the rewrite of this owner", "rewired %s" % OWNER in res, res[:160])
src = program(cmd)
kept, writes = C.blocks_for(src, OWNER)
check("70321 keeps a fragment for this owner", bool(kept.strip()) and kept != src, len(kept))
check("70321 excludes the other owner's name", OTHER not in kept, kept[-300:])
base = io.open(ACCEPTED, encoding="utf-8").read()
old = "prod_v2, prod_pos = SCO._to_v2_with_positions(produced)"
new = "prod_v2, prod_pos = SCO.eligible_produced(produced)"
check("the substitution's anchor is present exactly once in the accepted state",
      base.count(old) == 1, base.count(old))
got = base.replace(old, new)
check("applying it gives the reviewer's independent identity",
      hashlib.sha256(got.encode()).hexdigest() == WANT_70321,
      hashlib.sha256(got.encode()).hexdigest()[:16])
check("70321 is recognised as a write to this owner", writes is True, writes)

# ---- 75912: the helper calls ---------------------------------------------------
cmd, tid = use(75912)
rl, res, err = result_of(75912, tid)
check("75912 is the record the reviewer named",
      tid == "toolu_012Wpb8DudVxTG9LkFzM8P4t" and rl == 75913 and not err, (tid, rl, err))
src = program(cmd)
kept, writes = C.blocks_for(src, OWNER)
check("75912 is recognised as a write to this owner", writes is True, writes)
check("75912 keeps the helper this owner's calls need",
      "def edit(" in kept, kept[:120])
calls = [n for n in ast.walk(ast.parse(kept))
         if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "edit"]
check("75912 keeps exactly the three calls for this owner", len(calls) == 3, len(calls))
check("75912 excludes the other owner's preceding call",
      '"%s"' % OTHER not in kept and "'%s'" % OTHER not in kept, kept[:400])

bad = [n for n, ok in checks if not ok]
print("checks: %d  failed: %d  %s" % (len(checks), len(bad), bad[:4]))
sys.exit(1 if bad else 0)
