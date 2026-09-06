# -*- coding: utf-8 -*-
"""Replay ONE saved patch program on its own preimages (Codex SEQ 1737, rounds 2 and 3).

Same lawful path the accepted patch_1505 unit uses, with the record, the patch name and
the (preimage -> result) pairs given as arguments instead of written into the script, so
the later rounds' patches need no second copy of it.

The patch program is taken byte-exact out of its own record's heredoc, each preimage is
located BY HASH among the already-proved owners, and every declared result is asserted at
its COMPLETE recorded hash. A patch that edits files this replay does not seed stops when
it reaches one: that is accepted only when every declared target already holds its exact
recorded bytes, because the patch writes each file as soon as its own edits are applied.

Usage: patch_replay.py <record> <patch_name> <basename>:<pre_sha>:<post_sha> ...
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

A = os.path.dirname(os.path.abspath(__file__))
RAW = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
#: where an already-proved preimage may sit
POOLS = [A + "/proved", A + "/sources_a6", A + "/sources_ft", A + "/sources_a4"]

fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

record, patch_name = int(sys.argv[1]), sys.argv[2]
targets = [t.split(":") for t in sys.argv[3:]]
if not targets:
    sys.exit("REFUSE: no <basename>:<pre>:<post> target given")

cmd = tid = None
for c in (json.loads(io.open(RAW, encoding="utf-8", errors="replace")
                     .readlines()[record - 1]).get("message") or {}).get("content") or []:
    if isinstance(c, dict) and c.get("type") == "tool_use":
        cmd, tid = (c.get("input") or {}).get("command", ""), c.get("id")
if not cmd:
    sys.exit("REFUSE: record %d carries no command" % record)
m = re.search(r"cat > \S*/%s <<'PYEOF'\n(.*?)\nPYEOF" % re.escape(patch_name), cmd, re.S)
if not m:
    sys.exit("REFUSE: record %d does not save %s" % (record, patch_name))
body = m.group(1)
HERE = A + "/patches"
os.makedirs(HERE, exist_ok=True)
patch = os.path.join(HERE, patch_name)
io.open(patch, "w", encoding="utf-8", newline="").write(body + "\n")
print("record %d tool %s -> %s  %d bytes" % (record, tid, patch_name, len(body.encode())))
print("imports:", [l for l in body.splitlines() if l.startswith("import")])

WORK = HERE + "/work_" + os.path.splitext(patch_name)[0]
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK)
for name, pre, _post in targets:
    src = next((os.path.join(d, f) for d in POOLS if os.path.isdir(d)
                for f in sorted(os.listdir(d))
                if os.path.isfile(os.path.join(d, f))
                and fsha(os.path.join(d, f)) == pre), None)
    if src is None:
        sys.exit("REFUSE: no proved copy of %s at %s" % (name, pre[:16]))
    shutil.copyfile(src, os.path.join(WORK, name))
    print("seeded %-34s %s <- %s" % (name, pre[:16], os.path.relpath(src, A)))

r = subprocess.run([sys.executable, "-B", patch, WORK], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, timeout=300)
print("patch rc=%s %s" % (r.returncode, (r.stderr or "").strip().splitlines()[-1:] or ""))

bad, kept = [], []
for name, _pre, post in targets:
    p = os.path.join(WORK, name)
    got = fsha(p) if os.path.isfile(p) else "absent"
    print("%-34s -> %s  %s" % (name, got, "ok" if got == post else "WANT " + post))
    if got != post:
        bad.append(name)
        continue
    dst = "%s/proved/%s.%s.py" % (A, os.path.splitext(name)[0], post[:8])
    shutil.copyfile(p, dst)
    kept.append(os.path.basename(dst))
if bad:
    sys.exit("REFUSE: %s did not reach the recorded result" % bad)
print("KEPT", kept)
