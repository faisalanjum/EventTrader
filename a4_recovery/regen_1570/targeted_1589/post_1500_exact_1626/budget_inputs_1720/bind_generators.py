# -*- coding: utf-8 -*-
"""Bind every frozen generator to its OWN recorded result, by tool_use id.

The generator file must be the recorded command byte-for-byte, and the record
must carry exactly one later result with that id - no duplicate, no earlier
match - so a step can never be gated against another step's output.
"""
import hashlib, io, json, os, sys

RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
U = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/budget_inputs_1720")
GEN = os.environ.get("GEN_DIR", "generators")
sha = lambda b: hashlib.sha256(b).hexdigest()
lines = io.open(RAW, encoding="utf-8", errors="replace").readlines()

rows = []
for name in sorted(n[:-3] for n in os.listdir(U + "/" + GEN)):
    ln = int(name.split("_")[0])
    cmd = tid = None
    for c in ((json.loads(lines[ln - 1]).get("message") or {}).get("content") or []):
        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Bash":
            cmd, tid = (c.get("input") or {}).get("command", ""), c.get("id")
    if cmd is None:
        sys.exit("no Bash tool_use at line %d" % ln)
    frozen = io.open(U + "/" + GEN + "/" + name + ".sh", encoding="utf-8").read()
    if frozen != cmd:
        sys.exit("generator %s is not the recorded command byte-for-byte" % name)
    hits = []
    for n in range(ln, len(lines)):
        if tid not in lines[n]:
            continue
        for c in ((json.loads(lines[n]).get("message") or {}).get("content") or []):
            if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") == tid:
                x = c.get("content")
                if isinstance(x, list):
                    x = "".join(i.get("text", "") for i in x if isinstance(i, dict))
                hits.append((n + 1, x, bool(c.get("is_error"))))
    if len(hits) != 1:
        sys.exit("record %d: %d bound results (need exactly 1)" % (ln, len(hits)))
    rl, body, err = hits[0]
    if err:
        sys.exit("record %d bound result is an error" % ln)
    io.open(U + "/" + GEN.replace("generators", "results") + "/" + name + ".result.txt", "w", encoding="utf-8").write(body)
    rows.append((name, ln, tid, sha(cmd.encode()), rl, sha(body.encode()), len(body)))

with io.open(U + "/GENERATORS%s.tsv" % ("" if GEN == "generators" else "_g23"), "w", encoding="utf-8") as fh:
    fh.write("step\tline\ttool_use_id\tcommand_sha256\tresult_line\tresult_sha256\tresult_bytes\n")
    for r in rows:
        fh.write("%s\t%d\t%s\t%s\t%d\t%s\t%d\n" % r)
        print("%-22s line %-6d -> result %-6d cmd %s result %s"
              % (r[0], r[1], r[4], r[3][:16], r[5][:16]))
print("bound %d generators" % len(rows))
