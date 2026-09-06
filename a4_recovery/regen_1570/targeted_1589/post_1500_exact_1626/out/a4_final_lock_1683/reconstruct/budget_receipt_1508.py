# -*- coding: utf-8 -*-
"""The third round's call-budget receipt, from its CORRECTED original generator (SEQ 1739).

The generator itself is not built here. It arrives read-only through the map, at the path
its own round wrote it to: the pre-1509 generator carried by the recorded chain
(reconstruct/budget_chain/CHAIN.json, records 86148 -> 86765 -> 87058) with the saved patch
of original 87232 applied to a durable copy - a4_owner_1726/proved. Everything built on the
pre-1509 receipt is under superseded/ and is bound nowhere.

This stage runs that generator once and GATES on the recorded identity: a zero return code
without the exact receipt file hash is a failure.
"""
import hashlib, io, json, os, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
GEN = S + "/budget_receipt_1508.py"
OUT = "/tmp/a7_budget_receipt_1508.json"
#: the recorded identities this stage must reach (original 87232/87240; Codex SEQ 1739)
WANT_GEN = "43cb623295a4a2dc328ab61980bf4e5357a86fba5aec0a6ca02821593c0f3d9c"
WANT_RECEIPT = "ae27f66f2447dcf632345236cd0a4ec63aca6740628d723fa853caea1026d05a"
WANT_EMBEDDED = "a853a189e511490ea32107cacd08c94b292fbe340eb44f277e400fb0e7189b15"

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

got = sha(GEN)
print("generator %s  %d bytes" % (got, os.path.getsize(GEN)), flush=True)
if got != WANT_GEN:
    sys.exit("REFUSE: the bound generator is not the corrected one")
if os.path.exists(OUT):
    sys.exit("REFUSE: %s already exists; the corrected run writes it fresh" % OUT)

r = subprocess.run([PY3, "-B", "-u", GEN], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, cwd=H, timeout=900,
                   env=dict(os.environ, PYTHONPATH=H + ":/home/faisal/EventMarketDB"))
print((r.stdout or "").strip()[-1200:], flush=True)
if r.returncode:
    print((r.stderr or "")[-1200:], flush=True)
    sys.exit("REFUSE: the generator did not run")
if not os.path.isfile(OUT):
    sys.exit("REFUSE: %s was not written" % OUT)
got = sha(OUT)
doc = json.load(io.open(OUT, encoding="utf-8"))
print("RECEIPT %s %s" % (OUT, got), flush=True)
print("embedded receipt_sha256 %s  completed_before %s  ceiling %s  stages %d"
      % (doc.get("receipt_sha256"), doc.get("completed_before"), doc.get("ceiling"),
         len(doc.get("stages") or [])), flush=True)
if got != WANT_RECEIPT:
    sys.exit("REFUSE: the receipt is %s, not the recorded %s" % (got, WANT_RECEIPT))
if doc.get("receipt_sha256") != WANT_EMBEDDED:
    sys.exit("REFUSE: the embedded receipt hash is not the recorded one")
print("BUDGET_1508_OK", flush=True)
