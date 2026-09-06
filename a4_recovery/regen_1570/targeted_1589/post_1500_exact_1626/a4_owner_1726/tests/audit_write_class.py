# -*- coding: utf-8 -*-
"""Audit: no successful write to this owner is omitted or called a read (Codex 1727).

The oracle is the RAW tool result, not my classification: a record whose own successful
result names this file is a candidate write, and every such record must appear in the
recovery's table as something that changed the file. What the audit reports is the set
of records where the record's own evidence and my classification disagree.
"""
import io, json, os, re, sys

A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
OWNER = sys.argv[1] if len(sys.argv) > 1 else "a7_g23_build.py"
OPS = A + "/sources_a4/SOURCE_OPS.tsv"
LAST = int(sys.argv[2]) if len(sys.argv) > 2 else 84828
L = io.open(RAW, encoding="utf-8", errors="replace").readlines()

rows = {}
for ln in io.open(OPS, encoding="utf-8").read().splitlines()[1:]:
    c = ln.split("\t")
    rows[int(c[1])] = c[5]

changed = {n for n, cat in rows.items() if "applied" in cat or cat == "recorded-file-write"}
disagree = []
for n in range(1, LAST + 1):
    if OWNER not in L[n - 1]:
        continue
    tid = None
    for c in (json.loads(L[n - 1]).get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            tid = c.get("id")
    if not tid or n in changed:
        continue
    for m in range(n, len(L)):
        if tid not in L[m]:
            continue
        for c in (json.loads(L[m]).get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_result" \
                    and c.get("tool_use_id") == tid and not c.get("is_error"):
                x = c.get("content")
                if isinstance(x, list):
                    x = "".join(i.get("text", "") for i in x if isinstance(i, dict))
                if OWNER in (x or ""):
                    disagree.append((n, m + 1, rows.get(n, "not listed"),
                                     re.sub(r"\s+", " ", x)[:150]))
        break

print("records whose own successful result names %s but which changed nothing: %d"
      % (OWNER, len(disagree)))
for n, rl, cat, snip in disagree:
    print("   %6d -> result %-6d %-22s %s" % (n, rl, cat, snip))
