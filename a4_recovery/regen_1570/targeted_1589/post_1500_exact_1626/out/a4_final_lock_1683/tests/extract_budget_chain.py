# -*- coding: utf-8 -*-
"""Take the recorded derivation of the round-3 budget generator out of the transcript.

The live session store is not inside the projection, so the extraction happens HERE, on the
host, and the stage inside the boundary only runs what this wrote. From each record only the
one program that writes THAT generator is taken - an inline python heredoc, or the one sed
that redirects into it - and a record that carries anything but exactly one is refused.

Usage: extract_budget_chain.py <record>:<generator name> ...
"""
import hashlib
import io
import json
import os
import re
import sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = UNIT + "/reconstruct/" + (os.environ.get("CHAIN_DIR") or "budget_chain")
RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
HD = re.compile(r"python3 - (\"\$S\" )?<<'(\w+)'\n(.*?)\n\2$", re.S | re.M)

lines = io.open(RAW, encoding="utf-8", errors="replace").readlines()
os.makedirs(OUT, exist_ok=True)
steps = []
for arg in sys.argv[1:]:
    rec, name = arg.split(":")
    n = int(rec)
    cmd = tid = ""
    for c in (json.loads(lines[n - 1]).get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            cmd, tid = (c.get("input") or {}).get("command", "") or "", c.get("id")
    progs = [m for m in HD.finditer(cmd) if name in m.group(3)]
    seds = [l for l in cmd.splitlines()
            if l.lstrip().startswith("sed ") and name in l.split(">")[-1]]
    if len(progs) + len(seds) == 1:
        if progs:
            m = progs[0]
            kind, body = ("py_s" if m.group(1) else "py"), m.group(3) + "\n"
        else:
            kind, body = "sh", seds[0].strip() + "\n"
    elif len(progs) + len(seds) > 1:
        # A record that derives this file in more than one step is kept WHOLE: its own
        # command, unedited, is less interpretation than cutting it into pieces.
        kind, body = "sh_record", cmd + "\n"
    else:
        sys.exit("REFUSE: record %d carries no program writing %s" % (n, name))
    dst = os.path.join(OUT, "%d_%s.%s"
                       % (n, name[:-3], "py" if kind.startswith("py") else "sh"))
    io.open(dst, "w", encoding="utf-8", newline="").write(body)
    h = hashlib.sha256(body.encode()).hexdigest()
    steps.append({"record": n, "tool_use_id": tid, "writes": name, "kind": kind,
                  "program": os.path.basename(dst), "sha256": h})
    print("record %-6d %-24s %-4s %s  %d bytes" % (n, name, kind, h[:16], len(body.encode())))
io.open(OUT + "/CHAIN.json", "w", encoding="utf-8").write(
    json.dumps(steps, indent=1) + "\n")
print("CHAIN.json: %d steps" % len(steps))
