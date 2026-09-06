# -*- coding: utf-8 -*-
"""Durable projection, fail-forward placer (Codex SEQ 1695 item 2).

One pass: take the paths the REAL owners asked for and did not find (from the
runtime trace), resolve each through the CANONICAL final-A4 `OPENED.tsv` - which
pins both the exact byte and the logical location the historical run used - and
place the durable copy whose hash equals that pin.

ONE acceptance rule, no fallback (Codex SEQ 1700): a path is placed only when
the canonical OPENED pins it AND a durable copy has exactly that hash. A path
with no pin, or no durable copy matching it, is REPORTED as a candidate genuine
missing byte - never substituted by basename agreement, and never resolved by
scanning for a same-suffix directory. Placed bytes are re-hashed after the copy.

Extra bench-relative paths may be named on the command line; they go through the
same single rule, so naming one cannot loosen it.
"""
import hashlib
import io
import json
import os
import shutil
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
R70 = R + "/a4_recovery/regen_1570"
T = R70 + "/targeted_1589"
UNIT = T + "/post_1500_exact_1626/out/a4_final_lock_1683"
BENCH = UNIT + "/bench/bench_1306"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
OPENED = T + "/final_adjudication_1500/out/attempt5/A/OPENED.tsv"

# named durable roots to search for a pinned byte
SEARCH_ROOTS = [T + "/phase1_targeted_1488",
                R70 + "/foundation/a3/bench/.claude/plans/Drivers/experiments",
                # the durable A3 recovery bench: holds the canonical
                # `harness/` era bytes that foundation/a3 does not carry
                R + "/a3_recovery/regen_1541/bench/.claude/plans/Drivers/experiments",
                T + "/post_1500_exact_1626/inputs",
                T + "/final_adjudication_1500", T + "/hard_review_1495",
                T + "/targeted_run_1491", R70 + "/experiments",
                R70 + "/foundation/out",
                # durable recovery BENCH roots: carry the sibling authority
                # trees (FinalDesign/, WIP/) that live beside experiments/.
                # Never live main - independence from it is a requirement.
                R + "/a3_recovery/regen_1541/bench/.claude/plans/Drivers",
                R70 + "/foundation/a3/bench/.claude/plans/Drivers"]


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# canonical pins: logical bench-relative path -> sha256
pins = {}
for ln in io.open(OPENED, encoding="utf-8").read().splitlines()[1:]:
    c = ln.split("\t")
    if len(c) >= 3 and c[1].startswith("bench_1306/"):
        pins.setdefault(c[1][len("bench_1306/"):], c[2])

trace = json.load(io.open(UNIT + "/manifest/RED_PRIMARY_PATH.json", encoding="utf-8"))
wanted = list(sys.argv[1:])
for row in trace["missing_project_paths"]:
    p = row["path"]
    if not p.startswith("S/bench_1306/"):
        continue
    rel = p[len("S/bench_1306/"):]
    if row["kind"] in ("open", "isfile"):
        wanted.append(rel)
# An owner may reach a file through its own directory (`harness_g1v3/../keys`).
# The pin table names the normalized location, so normalize before the lookup -
# and refuse anything that normalizes outside the bench.
wanted = sorted({os.path.normpath(w) for w in wanted})
escapes = [w for w in wanted if os.path.isabs(w) or w.split("/")[0] == ".."]
if escapes:
    sys.exit("REFUSE path outside the bench: %s" % escapes)

placed, unpinned, unfound = [], [], []
for rel in wanted:
    want_sha = pins.get(rel)
    if not want_sha:
        unpinned.append(rel)
        continue
    dst = os.path.join(BENCH, rel)
    if os.path.isfile(dst) and fsha(dst) == want_sha:
        continue
    src = None
    base = os.path.basename(rel)
    for root in SEARCH_ROOTS:
        if src:
            break
        for dp, dn, fn in os.walk(root):
            if base in fn:
                c = os.path.join(dp, base)
                if os.path.isfile(c) and fsha(c) == want_sha:
                    src = c
                    break
    if src is None:
        unfound.append((rel, want_sha))
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != want_sha:
        unfound.append((rel, want_sha))
        continue
    placed.append((rel, want_sha, src))

man = UNIT + "/manifest/PROJECTION_PLACED.tsv"
mode = "a" if os.path.isfile(man) else "w"
with io.open(man, mode, encoding="utf-8") as fh:
    if mode == "w":
        fh.write("bench_rel\tsha256\tdurable_source\n")
    for rel, h, src in placed:
        fh.write("%s\t%s\t%s\n" % (rel, h, src.replace(R + "/", "")))

print("owners asked for (missing, open) : %d" % len(wanted))
print("placed from canonical pins       : %d" % len(placed))
for rel, h, _s in placed:
    print("   + %-58s %s" % (rel, h[:16]))
if unpinned:
    print("NOT PINNED by canonical OPENED (%d):" % len(unpinned))
    for r in unpinned:
        print("   ? %s" % r)
if unfound:
    print("PINNED BUT NO DURABLE COPY FOUND (%d)  <- candidate genuine missing byte:" % len(unfound))
    for r, h in unfound:
        print("   ! %-58s want %s" % (r, h[:16]))
sys.exit(1 if unfound else 0)
