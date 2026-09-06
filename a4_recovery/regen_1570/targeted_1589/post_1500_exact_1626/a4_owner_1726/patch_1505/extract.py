# -*- coding: utf-8 -*-
"""Take the saved patch_1505.py out of its own record, byte-exact (Codex SEQ 1737)."""
import io, json, re, sys
RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
A = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/a4_owner_1726")
L = io.open(RAW, encoding="utf-8", errors="replace").readlines()
cmd = tid = None
for c in (json.loads(L[86107]).get("message") or {}).get("content") or []:
    if isinstance(c, dict) and c.get("type") == "tool_use":
        cmd, tid = (c.get("input") or {}).get("command", ""), c.get("id")
if not cmd:
    sys.exit("REFUSE: record 86108 carries no command")
print("record 86108 tool id:", tid)
m = re.search(r"cat > \$S/patch_1505\.py <<'PYEOF'\n(.*?)\nPYEOF", cmd, re.S)
if not m:
    sys.exit("REFUSE: the saved patch is not in this record")
body = m.group(1)
io.open(A + "/patch_1505/patch_1505.py", "w", encoding="utf-8", newline="").write(body + "\n")
print("saved patch: %d bytes" % len(body.encode()))
print("imports:", [l for l in body.splitlines() if l.startswith("import")])
print("edits:", re.findall(r'p\s*=\s*H\s*\+\s*"(/[\w.]+)"', body))
