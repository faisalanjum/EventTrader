# -*- coding: utf-8 -*-
"""Replay the accepted v9 key-correction generator chain (Codex SEQ 1713/1714).

Every step is the recorded command itself, byte-for-byte out of the frozen
transcript; nothing is paraphrased and no value is typed. The one input the
chain needs that no longer exists on disk - the workflow task output the probe
writer read - is RECONSTRUCTED from the frozen official state by the runtime's
own seven-field projection, and accepted only at its recorded hash and length.

A step is accepted only when every line of its recorded result reappears in the
replay's own output, so a step that drifts by one count or one hash fails here
rather than passing a wrong ledger forward.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
K = os.environ["KEY_UNIT"]
KEEP = os.environ["KEEP_DIR"]
# every workflow task output the recorded writers read, each reconstructed from
# its own frozen official state by the runtime's seven-field projection
TASK_OUTS = json.loads(os.environ["TASK_OUTPUTS"])

sha = lambda b: hashlib.sha256(b).hexdigest()
# the chain order is the transcript order, so it is read from the frozen
# generator names rather than kept by hand
STEPS = sorted(n[:-3] for n in os.listdir(os.path.join(os.environ["KEY_UNIT"], "generators")))
NOISE = ("Shell cwd was reset",)


def fail(msg):
    print("REFUSED: " + msg)
    sys.exit(2)


# ---- the one absent input, reconstructed by the runtime's own projection ----
for state_path, out_path, pin in TASK_OUTS:
    d = json.load(io.open(state_path, encoding="utf-8"))
    env = {}
    for k in ("summary", "agentCount", "logs", "result"):
        env[k] = d.get(k)
    env["workflowProgress"] = [r for r in d.get("workflowProgress", [])
                               if r.get("type") != "workflow_log"]
    env["totalTokens"] = d.get("totalTokens")
    env["totalToolCalls"] = d.get("totalToolCalls")
    body = json.dumps(env, indent=1).encode()
    if pin and sha(body) != pin:
        fail("the reconstructed task output is %s, not %s" % (sha(body)[:16], pin[:16]))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").write(body)
    print("ok   task output reconstructed  %s  %d bytes  <- %s"
          % (sha(body)[:16], len(body), os.path.basename(state_path)))

# ---- the recorded chain, in order, each gated on its own recorded result ----
for name in STEPS:
    script = os.path.join(K, "generators", name + ".sh")
    want = io.open(os.path.join(K, "results", name + ".result.txt"),
                   encoding="utf-8").read()
    # One recorded generator iterates a SET of row identities, so the row ORDER
    # inside the written ledger depends on Python's per-process hash seed. The
    # applied key is order-free and always matches; the ledger FILE bytes are not.
    # The seed is therefore pinned, and the recorded ledger hash is what decides
    # whether the pinned value is the historical one - it is never assumed.
    r = subprocess.run(["bash", script], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONHASHSEED=os.environ["HASH_SEED"]))
    got = (r.stdout or "") + (r.stderr or "")
    # the historical capture was a `tail`, so the recorded result IS the tail of
    # the step's output: require it as an exact contiguous suffix
    wl = [l for l in want.splitlines() if l.strip() and not any(n in l for n in NOISE)]
    gl = [l for l in got.splitlines() if l.strip() and not any(n in l for n in NOISE)]
    missing = [] if gl[-len(wl):] == wl else wl
    print("%s %-20s rc=%s  recorded lines %d, suffix match %s"
          % ("ok  " if not missing and r.returncode == 0 else "BAD ", name,
             r.returncode, len(wl), not missing))
    if missing:
        for a, b_ in list(zip(wl, gl[-len(wl):]))[:6]:
            if a != b_:
                print("      recorded: %s" % a[:140])
                print("      replayed: %s" % b_[:140])
        print("   --- replay output tail ---")
        print("\n".join(got.strip().splitlines()[-12:]))
        # keep what the failing step produced, so the divergence can be read
        os.makedirs(KEEP + "/failed", exist_ok=True)
        for q in ("/tmp/a7_key_v8_correction.json", "/tmp/a7_key_v9_correction.json",
                  "/tmp/a7_final_route_inventory.v2.json", "/tmp/a7_key_v9_gold.json"):
            if os.path.isfile(q):
                shutil.copyfile(q, os.path.join(KEEP, "failed", os.path.basename(q)))
        if os.environ.get("DIAGNOSTIC") != "1":
            fail("step %s did not reproduce its recorded result" % name)
        print("   DIAGNOSTIC: continuing past this mismatch to locate the divergence")

# ---- preserve every artifact the chain produced -----------------------------
os.makedirs(KEEP, exist_ok=True)
kept = []
for p in ("/tmp/a7_key_v9_correction.json", "/tmp/a7_key_v8_correction.json",
          "/tmp/a7_key_v9_gold.json", "/tmp/a7_final_route_inventory.v2.json",
          "/tmp/a7_period_actions.json", "/tmp/a7_period_stops.json",
          "/tmp/a7_route_stops.json", "/tmp/a7_dri_restored_sibling.json",
          "/tmp/a7_od1_run_v2/official_result.json", "/tmp/a7_od1_run_v2/verdicts.json",
          "/tmp/a7_key_v7_gold.json") + tuple(o for _s, o, _p in TASK_OUTS):
    if os.path.isfile(p):
        dst = os.path.join(KEEP, os.path.basename(p))
        shutil.copyfile(p, dst)
        kept.append((os.path.basename(p), sha(open(dst, "rb").read()), os.path.getsize(dst)))
with io.open(os.path.join(KEEP, "ARTIFACTS.tsv"), "w", encoding="utf-8") as fh:
    fh.write("file\tsha256\tbytes\n")
    for n, h, b in sorted(kept):
        fh.write("%s\t%s\t%d\n" % (n, h, b))
        print("kept %-38s %s %8d B" % (n, h[:16], b))
print("PRESERVED %d artifacts" % len(kept))
