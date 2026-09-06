# -*- coding: utf-8 -*-
"""Check the signed A4 checkpoint WITHOUT rebuilding anything (Codex SEQ 1742 item 4).

The completed operations are write-once and refuse a second run, so the handoff needs a
read-only way to confirm the checkpoint still holds. This asks the existing owners:
the lock's own verify() re-derives every bound value from the live bytes, and the ten bound
inputs, the lock and its receipt are re-hashed. Nothing is written.
"""
import collections, hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
LOCKDIR = S + "/lock"
sys.path.insert(0, LOCKDIR); sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_final_key_lock as L                                   # noqa: E402

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
WANT = {"lock": "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0",
        "receipt": "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3"}

bad = []
for name, p in (("lock", L.LOCK), ("receipt", L.RECEIPT)):
    if not os.path.isfile(p):
        bad.append("%s is absent" % name)
        continue
    got = sha(p)
    print("%-8s %s" % (name, got), flush=True)
    if got != WANT[name]:
        bad.append("%s is %s" % (name, got))
for k, p in L.BOUND.items():
    print("   %-18s %s" % (k, sha(p) if os.path.isfile(p) else "ABSENT"), flush=True)
    if not os.path.isfile(p):
        bad.append("bound input absent: %s" % k)
if not bad:
    lock = json.load(io.open(L.LOCK, encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    problems = L.verify(lock)
    acc = lock["call_accounting"]
    print("verify problems: %r" % (problems,), flush=True)
    print("call accounting %s" % json.dumps(acc), flush=True)
    if problems:
        bad += problems
    if (acc["ledger_before"], acc["ledger_after"], acc["signer_calls"], acc["retries"]) \
            != (5219, 5220, 1, 0):
        bad.append("the call accounting moved")
if bad:
    print("REFUSED: %r" % (bad[:5],), flush=True)
    sys.exit(1)
print("CHECKPOINT_OK", flush=True)
