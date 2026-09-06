# -*- coding: utf-8 -*-
"""Audit: every command that both edits and writes this file must do both (SEQ 1728).

A row that merely changed is not proof: a record that appends to the file will change it
whether or not the edits before the append were applied. So the audit finds the records
that carry BOTH an edit program and a shell write to this owner, and requires each to be
handled as the mixed case rather than as a bare file write.
"""
import io, json, os, re, sys

A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, A)
import recover_a4_owner as C                                    # noqa: E402

RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
OWNER = sys.argv[1] if len(sys.argv) > 1 else "a7_g23_build.py"
LAST = int(sys.argv[2]) if len(sys.argv) > 2 else 84828
OPS = A + "/sources_a4/SOURCE_OPS.tsv"
L = io.open(RAW, encoding="utf-8", errors="replace").readlines()
rows = {int(l.split("\t")[1]): l.split("\t")[5]
        for l in io.open(OPS, encoding="utf-8").read().splitlines()[1:]}

mixed, unhandled = [], []
for n in range(1, LAST + 1):
    if OWNER not in L[n - 1]:
        continue
    cmd = None
    for c in (json.loads(L[n - 1]).get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            cmd = (c.get("input") or {}).get("command", "")
    if not cmd:
        continue
    writes = [m for m in C.HD.finditer(cmd) if m.group(2).strip("\"'").endswith(OWNER)]
    # A PROGRAM IN THE SAME COMMAND IS ONLY THE OTHER HALF WHEN IT WRITES THIS FILE.
    # The test is the caller's own per-owner extraction, so the audit cannot disagree
    # with the recovery about what a mixed command is, only about whether it ran.
    progs = [m for m in C.HD_Q.finditer(cmd)
             if "python" in cmd[:m.start()].split("\n")[-1]
             and not any(w.start() <= m.start() < w.end() for w in writes)
             and C.blocks_for(m.group(3), OWNER)[1]]
    if not (writes and progs):
        continue
    mixed.append(n)
    # a mixed record must NOT be recorded as a bare file write: that label is what
    # dropped the program half
    if rows.get(n) == "recorded-file-write":
        unhandled.append(n)

print("commands that both edit and write %s: %d %s" % (OWNER, len(mixed), mixed))
print("still handled as a bare file write: %d %s" % (len(unhandled), unhandled))
sys.exit(1 if unhandled else 0)
