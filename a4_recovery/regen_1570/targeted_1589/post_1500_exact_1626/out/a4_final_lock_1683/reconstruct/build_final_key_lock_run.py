# -*- coding: utf-8 -*-
"""Run the existing saved lock builder ONCE and gate its recorded identities (SEQ 1741 item 4).

The builder is the historical one: it binds only identities that already exist, re-derives
every bound value, writes the lock and its receipt once, and runs its own mutation checks -
every bound value must refuse when mutated. Nothing is added here; this stage runs it and
refuses unless the lock, the receipt, the mutation result and the call accounting are the
recorded ones.
"""
import hashlib, io, json, os, re, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
BUILDER = S + "/lock/build_final_key_lock.py"
OUT = S + "/lock/final_key_candidate_1511"
LOCK, RECEIPT = OUT + "/a4_final_key_lock.json", OUT + "/a4_final_key_lock_receipt.json"
WANT_LOCK = "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"
WANT_RECEIPT = "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3"
WANT_AFTER = 5220

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
for p in (LOCK, RECEIPT):
    if os.path.exists(p):
        sys.exit("REFUSE: %s already exists; the lock is written once" % p)

r = subprocess.run([PY3, "-B", "-u", BUILDER], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, cwd=H, timeout=1800,
                   env=dict(os.environ, PYTHONPATH=H + ":/home/faisal/EventMarketDB"))
print((r.stdout or "").strip()[-3000:], flush=True)
if r.returncode:
    print((r.stderr or "")[-1200:], flush=True)
    sys.exit("REFUSE: the lock builder returned %d" % r.returncode)
if "EVERY BOUND VALUE REFUSES WHEN MUTATED" not in (r.stdout or ""):
    sys.exit("REFUSE: the builder's own mutation checks did not all refuse")

for name, path, want in (("lock", LOCK, WANT_LOCK), ("receipt", RECEIPT, WANT_RECEIPT)):
    if not os.path.isfile(path):
        sys.exit("REFUSE: %s was not written" % name)
    got = sha(path)
    print("%-8s %s" % (name, got), flush=True)
    if got != want:
        sys.exit("REFUSE: the %s is %s, not the recorded %s" % (name, got, want))

lock = json.load(io.open(LOCK, encoding="utf-8"))
acc = lock["call_accounting"]
print("call accounting %s" % json.dumps(acc), flush=True)
if (acc["ledger_after"], acc["signer_calls"], acc["retries"]) != (WANT_AFTER, 1, 0):
    sys.exit("REFUSE: the call accounting is not %d from one signer call" % WANT_AFTER)
rec = json.load(io.open(RECEIPT, encoding="utf-8"))
n_ref = sum(1 for v in rec["mutations"].values() if v == "refused")
print("mutations %d/%d refused; live verify problems %r"
      % (n_ref, len(rec["mutations"]), rec["verify_problems_on_the_live_bytes"]), flush=True)
if n_ref != len(rec["mutations"]) or rec["verify_problems_on_the_live_bytes"]:
    sys.exit("REFUSE: a mutation was accepted or the live lock does not verify")
print("LOCK_OK", flush=True)
