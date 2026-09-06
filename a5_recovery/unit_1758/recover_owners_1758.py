# -*- coding: utf-8 -*-
"""Core SEQ 1757 / Codex SEQ 1758 step 2 - recover the exact A5-era owners.

The only owner needing reconstruction is raw_transport.py. Its two edits are
recorded literally inside the durable helper reconstruct_pre_1514.py, which
applies them BACKWARD; the A5-era bytes are the same pairs applied FORWARD to
the pre-edit file. The pairs are read out of that helper by parsing it, never
retyped, so a transcription slip cannot enter the owner.
"""
import ast
import hashlib
import io
import os
import shutil
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
U = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
H = R + "/a4_recovery/regen_1570/targeted_1589/phase1_targeted_1488/inputs/harness_g1v3"
HELPER = ("/home/faisal/.core827_backups/recovery_1531/model/tmp/claude-1000"
          "/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
          "/scratchpad/reconstruct_pre_1514.py")
UNIT = os.path.dirname(os.path.abspath(__file__))
OWNERS = UNIT + "/owners"
EV = UNIT + "/evidence"

# what Codex pinned, so a wrong result cannot be published as right
WANT = {
    "helper": "d4899a06b65073ad2c3ef58e16a83d873ed75b6569df8ed2023c32802dac62b6",
    "rt_pre": "05b02f5bb67944d39fcf726da043f768d5d640bddbe18754ce3c3ef6c4bc10de",
    "rt_a5": "02f51e5a8a8bd87d3a97eb44aeae57ba127492a9bebdb8df3f1471d8859fae4b",
    "rt_a5_bytes": 86750,
}
CHECKS = []


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fsha(p):
    return sha(io.open(p, "rb").read())


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %-46s %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:70],
                             "" if ok else "   != %s" % str(want)[:70]), flush=True)


def edit_pairs(helper_src, owner_basename):
    """The (old, new) literals the helper records for one owner, in order."""
    tree = ast.parse(helper_src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", None) != "rev":
            continue
        target = ast.get_source_segment(helper_src, node.args[0]) or ""
        if owner_basename not in target:
            continue
        return [(ast.literal_eval(e.elts[0]), ast.literal_eval(e.elts[1]))
                for e in node.args[1].elts]
    raise SystemExit("REFUSED: the helper records no edits for %s" % owner_basename)


os.makedirs(OWNERS, exist_ok=True)
os.makedirs(EV, exist_ok=True)

src = io.open(HELPER, encoding="utf-8").read()
check("the recorded helper is the pinned one", sha(src.encode("utf-8")), WANT["helper"])
check("the pre-edit raw_transport is the pinned one", fsha(H + "/raw_transport.py"), WANT["rt_pre"])

pairs = edit_pairs(src, "raw_transport.py")
check("the helper records two raw_transport edits", len(pairs), 2)

text = io.open(H + "/raw_transport.py", encoding="utf-8").read()
log = []
for i, (old, new) in enumerate(pairs, 1):
    check("edit %d matches the pre-edit file exactly once" % i, text.count(old), 1)
    check("edit %d is not already applied" % i, text.count(new), 0)
    text = text.replace(old, new)
    log.append("edit %d\n--- recorded old ---\n%s\n--- recorded new ---\n%s\n" % (i, old, new))

out = text.encode("utf-8")
check("recovered raw_transport size", len(out), WANT["rt_a5_bytes"])
check("recovered raw_transport sha256", sha(out), WANT["rt_a5"])

bad = [n for n, ok in CHECKS if not ok]
if bad:
    print("REFUSED: nothing written; failed %s" % bad)
    sys.exit(2)

io.open(OWNERS + "/raw_transport.py", "wb").write(out)
io.open(EV + "/raw_transport_edits.txt", "w", encoding="utf-8").write("\n".join(log))

# the owners that already exist byte-exact are copied, never rebuilt
for src_path, name in ((H + "/build_a5_exp5_kit.py", "build_a5_exp5_kit.py"),
                       (H + "/build_launch_manifest.py", "build_launch_manifest.py"),
                       (H + "/audit_worker_access.py", "audit_worker_access.py"),
                       (H + "/scorers/score_exp5.py", "scorers/score_exp5.py"),
                       (H + "/test_a5_corrected_inventory_1514.py", "test_a5_corrected_inventory_1514.py")):
    dst = os.path.join(OWNERS, name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src_path, dst)
    print("copied %-40s %s" % (name, fsha(dst)[:16]))

print("RECOVER_OWNERS_1758_OK  checks %d  failed 0" % len(CHECKS))
