# -*- coding: utf-8 -*-
"""Take the round-2 saved patch out of its own record, byte-exact (Codex SEQ 1737).

Record 86234 writes patch_1505b.py, whose twelve literal replacements carry the bind-era
owner to the round-2 preflight/prepare owner the reviewer pins at 86601.
"""
import io, json, re, sys
RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
A = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/a4_owner_1726")
L = io.open(RAW, encoding="utf-8", errors="replace").readlines()
cmd = tid = None
for c in (json.loads(L[86233]).get("message") or {}).get("content") or []:
    if isinstance(c, dict) and c.get("type") == "tool_use":
        cmd, tid = (c.get("input") or {}).get("command", ""), c.get("id")
if not cmd:
    sys.exit("REFUSE: record 86234 carries no command")
print("record 86234 tool id:", tid)
m = re.search(r"cat > \$S/patch_1505b\.py <<'PYEOF'\n(.*?)\nPYEOF", cmd, re.S)
if not m:
    sys.exit("REFUSE: the round-2 saved patch is not in this record")
body = m.group(1)
io.open(A + "/patch_1505/patch_1505b.py", "w", encoding="utf-8", newline="").write(body + "\n")
print("saved patch: %d bytes" % len(body.encode()))
print("imports:", [l for l in body.splitlines() if l.startswith("import")])
print("edits:", re.findall(r'p\s*=\s*H\s*\+\s*"(/[\w.]+)"', body))
print("replacements:", body.count("rep("))
