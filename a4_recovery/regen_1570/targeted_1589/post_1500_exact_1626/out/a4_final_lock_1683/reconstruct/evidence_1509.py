# -*- coding: utf-8 -*-
"""The round-3 evidence helper the binding gate calls, from its own recorded derivation.

`bind_1509` proves the two saved answers through `$S/evidence_1509.py`. That helper was never
saved whole: it is the SEQ 1495 helper (Write record 83364, recovered byte-exact and kept
durable) carried forward by one recorded step per round - 84642, 85843, 86600, 87340 - each
taken out of its own record by tests/extract_budget_chain.py.

Read-only work: every step is a text transform of the previous helper. The stage refuses if
the final helper is absent or cannot answer the gate's own subcommands.
"""
import hashlib, io, json, os, shutil, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
P = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626")
UNIT = P + "/out/a4_final_lock_1683"
CHAIN_DIR = UNIT + "/reconstruct/evidence_chain"
BASE = P + "/a4_owner_1726/proved/evidence_1495.py"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
TARGET = S + "/evidence_1509.py"

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
steps = json.load(io.open(CHAIN_DIR + "/CHAIN.json", encoding="utf-8"))

# The helper this unit already produced is bound back read-only, and its steps EDIT their
# own file in place - so the chain is walked only when the round-3 helper is not there yet.
if not os.path.isfile(TARGET):
    first = os.path.join(S, os.path.basename(BASE))
    shutil.copyfile(BASE, first)
    print("base %s %s  %d bytes"
          % (os.path.basename(BASE), sha(first)[:16], os.path.getsize(first)), flush=True)
    steps_to_run = steps
else:
    print("the round-3 helper is already present %s" % sha(TARGET)[:16], flush=True)
    steps_to_run = []

for st in steps_to_run:
    prog = os.path.join(CHAIN_DIR, st["program"])
    if sha(prog) != st["sha256"]:
        sys.exit("REFUSE: %s is not the extracted program" % st["program"])
    made = os.path.join(S, st["writes"])
    body = io.open(prog, encoding="utf-8").read()
    if st["kind"] == "sh_record":
        argv = ["bash", "-c", body]
    elif st["kind"] == "sh":
        argv = ["bash", "-c", "S=%s; %s" % (S, body)]
    else:
        argv = [PY3, "-B", prog] + ([S] if st["kind"] == "py_s" else [])
    was = sha(made) if os.path.isfile(made) else None
    r = subprocess.run(argv, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       cwd=H, timeout=600)
    print("record %-6d %-22s rc=%s" % (st["record"], st["writes"], r.returncode), flush=True)
    if not os.path.isfile(made):
        print((r.stderr or "")[-700:], flush=True)
        sys.exit("REFUSE: %s was not written" % st["writes"])
    # A step that also touched files this projection does not carry may exit non-zero
    # AFTER writing its own; that is only acceptable when this file actually changed.
    if r.returncode and sha(made) == was:
        print((r.stderr or "")[-700:], flush=True)
        sys.exit("REFUSE: record %d failed and left %s unchanged" % (st["record"], st["writes"]))
    print("   %-22s %s  %d bytes"
          % (st["writes"], sha(made)[:16], os.path.getsize(made)), flush=True)

if not os.path.isfile(TARGET):
    sys.exit("REFUSE: the round-3 evidence helper was not produced")
print("HELPER %s %s" % (TARGET, sha(TARGET)), flush=True)
for sub in ("completed", "agents", "tools", "reads", "mid", "modelset"):
    r = subprocess.run([PY3, "-B", TARGET, sub], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, cwd="/home/faisal/EventMarketDB", timeout=300)
    out = (r.stdout or "").strip()
    print("   %-9s rc=%s %s" % (sub, r.returncode, out[:120]), flush=True)
    if r.returncode or not out:
        print((r.stderr or "")[-400:], flush=True)
        sys.exit("REFUSE: the helper cannot answer %r" % sub)
print("EVIDENCE_1509_OK", flush=True)
