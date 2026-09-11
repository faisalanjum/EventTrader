# -*- coding: utf-8 -*-
"""Codex SEQ 2017: DERIVE the final source-key binding from the review one.

Input  : unit_2015_real_reviews/map_real_launch_2015.tsv - the binding that
         served the four real clarified reviews and their closeout.
Output : the same binding with exactly two kinds of edit, every changed or new
         pin re-measured here by the boundary's own hasher:

  1. the one writable row now writes into THIS unit, so the completed review
     package and run cannot be written at all;
  2. two new scoped rows re-serve the COMPLETED review run and package
     READ-ONLY at the logical paths they already occupy, from their durable
     unit_2015 copies.

Every other row is carried through untouched: the original 2004 run and
package, the source-only 1997 inputs, the clarified harness, the issuer
context, the approved lane-input artifact and all three recorded launch paths.

Usage: make_map_2017.py <out.tsv>
"""
import io
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_UNIT = os.path.join(A7, "unit_2015_real_reviews")
SOURCE_MAP = os.path.join(REVIEW_UNIT, "map_real_launch_2015.tsv")
OLD_ROOT = os.path.join(REVIEW_UNIT, "key_closure")
NEW_ROOT = os.path.join(HERE, "key_closure")
COMPLETED = ("review_2015", "closure_2015")
OUT = sys.argv[1]

rows = boundary.read_map(SOURCE_MAP)
bad = boundary.validate(rows)
assert not bad, bad                    # the review binding still measures clean

out, edits = [], []
for row in rows:
    row = dict(row)
    if row["source"] == OLD_ROOT:
        assert row["mode"] == "rw" and row["sha"] == "-", row
        row["source"] = NEW_ROOT
        edits.append(("fresh output root", row["logical"]))
        out.append(row)
        for name in COMPLETED:         # the completed stage, read-only, in place
            src = os.path.join(OLD_ROOT, name)
            out.append({"logical": row["logical"] + "/" + name, "source": src,
                        "sha": boundary.source_sha(src), "mode": "ro"})
            edits.append(("completed read-only", row["logical"] + "/" + name))
        continue
    out.append(row)

assert [e[0] for e in edits] == ["fresh output root", "completed read-only",
                                 "completed read-only"], edits
assert len(out) == len(rows) + len(COMPLETED)
changed = {e[1] for e in edits}
before = {r["logical"]: r for r in rows}
for r in out:
    if r["logical"] not in changed:
        assert r == before[r["logical"]], r
bad = boundary.validate(out)
assert not bad, bad

with io.open(OUT, "x", encoding="utf-8") as fh:
    fh.write("".join("\t".join(r[k] for k in ("logical", "source", "sha", "mode"))
                     + "\n" for r in out))
print(OUT)
for kind, logical in edits:
    print("  %-20s %s" % (kind, logical))
