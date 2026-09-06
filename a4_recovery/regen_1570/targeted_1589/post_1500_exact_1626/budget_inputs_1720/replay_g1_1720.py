# -*- coding: utf-8 -*-
"""Replay the recorded chain that writes the three budget-receipt inputs
(Codex SEQ 1720).

Every step is the recorded command itself, byte-for-byte out of the frozen
transcript. A step is accepted only when its recorded result reappears as an
exact contiguous suffix of the replay's own output - the historical capture was
a `tail` - so a step that drifts by one count or one hash fails here instead of
carrying a wrong candidate forward.

The chain order is the transcript order, read from the frozen generator names
rather than kept by hand. STOP_AFTER runs the chain up to one named step, so a
later era's owners are seeded before that era's steps are reached.
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys

K = os.environ["G1_UNIT"]
KEEP = os.environ["KEEP_DIR"]
STOP = os.environ.get("STOP_AFTER") or ""
sha = lambda b: hashlib.sha256(b).hexdigest()
#: which frozen generator set this replay runs
GEN = os.environ.get("GEN_DIR", "generators")
STEPS = sorted(n[:-3] for n in os.listdir(os.path.join(K, GEN)))
if STOP:
    STEPS = STEPS[:STEPS.index(STOP) + 1]
NOISE = ("Shell cwd was reset",)
#: what the chain must produce - the three demanded files and the candidate
#: every one of them is pinned against
WANT = {
    "/tmp/a7_g1_v16_event/a7_g1_candidate.json":
        "efcf41c5041f774bf9bd2950b26d6667665dd3c9cd52415d88e2c34673a8a45e",
    "/tmp/a7_g1_event_run4/root.json":
        "b491596136682a696876844bedd656c5cc71ff73b323f1be87d307514df3cf81",
    "/tmp/a7_g2_candidate/a7_g1_candidate.json":
        "21ae14e50050780e6dcac5451c72a4ed5d96b283d38f6f8cd78de2dccc180d19",
    "/tmp/a7_g3_candidate/a7_g1_candidate.json":
        "53a60ec15228c685b27da89b0bf4ff6c86ece4c78dbe3b9fff127f1040ae0c3a",
    "/tmp/a7_reference_inventory.json":
        "ae81caf4936c43432fe27d5ac686dfa090539c615620ce029eaeb00b2f900106",
}


def fail(msg):
    print("REFUSED: " + msg)
    sys.exit(2)


for name in STEPS:
    script = os.path.join(K, GEN, name + ".sh")
    want = io.open(os.path.join(K, GEN.replace("generators", "results"), name + ".result.txt"),
                   encoding="utf-8").read()
    r = subprocess.run(["bash", script], capture_output=True, text=True)
    got = (r.stdout or "") + (r.stderr or "")
    wl = [l for l in want.splitlines() if l.strip() and not any(n in l for n in NOISE)]
    gl = [l for l in got.splitlines() if l.strip() and not any(n in l for n in NOISE)]
    missing = [] if gl[-len(wl):] == wl else wl
    print("%s %-22s rc=%s  recorded lines %d, suffix match %s"
          % ("ok  " if not missing and r.returncode == 0 else "BAD ", name,
             r.returncode, len(wl), not missing), flush=True)
    if missing:
        for a, b_ in list(zip(wl, gl[-len(wl):]))[:8]:
            if a != b_:
                print("      recorded: %s" % a[:150])
                print("      replayed: %s" % b_[:150])
        print("   --- replay output tail ---")
        print("\n".join(got.strip().splitlines()[-15:]))
        fail("step %s did not reproduce its recorded result" % name)

# ---- preserve every demanded artifact, each at its own pin ------------------
os.makedirs(KEEP, exist_ok=True)
kept, absent = [], []
for p, pin in sorted(WANT.items()):
    if not os.path.isfile(p):
        absent.append(p)
        continue
    got = sha(io.open(p, "rb").read())
    if pin and got != pin:
        fail("%s is %s, not its pinned %s" % (p, got[:16], pin[:16]))
    dst = os.path.join(KEEP, p.strip("/").replace("/", "__"))
    shutil.copyfile(p, dst)
    kept.append((os.path.basename(dst), got, os.path.getsize(dst)))
with io.open(os.path.join(KEEP, "ARTIFACTS.tsv"), "w", encoding="utf-8") as fh:
    fh.write("file\tsha256\tbytes\n")
    for n, h, b in sorted(kept):
        fh.write("%s\t%s\t%d\n" % (n, h, b))
        print("kept %-52s %s %9d B" % (n, h[:16], b))
for p in absent:
    print("not produced by this leg of the chain: %s" % p)
print("PRESERVED %d artifacts" % len(kept))
