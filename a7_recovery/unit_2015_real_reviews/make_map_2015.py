# -*- coding: utf-8 -*-
"""Codex SEQ 2015: DERIVE the real four-review binding from the live one.

Input  : unit_2004/map_review_live_2005.tsv - the verified live review binding
         that served the 66 primaries and their invalid-only child.
Output : map_real_2015.tsv - the same binding with exactly three edits, every
         changed pin re-measured here by the boundary's own hasher:

  1. the two rows that serve the review harness now serve the PUBLISHED
     CLARIFIED harness (unit_2008/harness_g1v3) instead of the original
     unit_1997 one;
  2. the one rw row now writes into THIS unit, so no historical directory can
     be written at all;
  3. two new scoped rows re-serve the ORIGINAL run and package READ-ONLY at
     their own logical paths;
  4. one read-only row per preserved attempt re-serves the LAUNCH PATH that
     attempt's own official states recorded, so the original finalizer can
     still read back every script it launched. The directory is taken from the
     states the receipt names - never typed here - and the live binding's own
     primary row must come out identical, which is the check that it is.

Nothing else is touched: the source inventory, the native store (absent from
this map, so the real one is read natively), the issuer context and every
other pin stay exactly as the live binding had them.
"""
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402

LIVE = os.path.join(A7, "unit_2004/map_review_live_2005.tsv")
OUT = sys.argv[1]
OLD_HARNESS = os.path.join(A7, "unit_1997/harness_g1v3")
NEW_HARNESS = os.path.join(A7, "unit_2008/harness_g1v3")
OLD_ROOT = os.path.join(A7, "unit_2004/key_closure")
NEW_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key_closure")
PRESERVED = ("review_2004", "closure_2004")

rows = boundary.read_map(LIVE)
bad = boundary.validate(rows)
assert not bad, bad                       # the live binding still measures clean

out, edits = [], []
for row in rows:
    row = dict(row)
    if row["source"] == OLD_HARNESS:
        assert row["mode"] == "ro", row
        row["source"] = NEW_HARNESS
        row["sha"] = boundary.source_sha(NEW_HARNESS)
        edits.append(("clarified harness", row["logical"]))
    elif row["source"] == OLD_ROOT:
        assert row["mode"] == "rw" and row["sha"] == "-", row
        row["source"] = NEW_ROOT
        edits.append(("fresh output root", row["logical"]))
        out.append(row)
        for name in PRESERVED:            # the originals, read-only, in place
            src = os.path.join(OLD_ROOT, name)
            out.append({"logical": row["logical"] + "/" + name, "source": src,
                        "sha": boundary.source_sha(src), "mode": "ro"})
            edits.append(("preserved read-only", row["logical"] + "/" + name))
        continue
    out.append(row)

assert [e[0] for e in edits] == ["clarified harness", "clarified harness",
                                 "fresh output root", "preserved read-only",
                                 "preserved read-only"], edits
assert len(out) == len(rows) + len(PRESERVED)
# every row that is not one of the five edited logical paths is byte-identical
changed = {e[1] for e in edits}
before = {r["logical"]: r for r in rows}
for r in out:
    if r["logical"] in changed:
        continue
    assert r == before[r["logical"]], r
# --- the launch path each preserved attempt actually recorded -------------
seen = {r["logical"]: r for r in out}
RUN_NAME, PKG_NAME = PRESERVED                   # only the run has attempts
base = os.path.join(OLD_ROOT, RUN_NAME)
for attempt in (base, os.path.join(base, "retry")):
    receipt = os.path.join(attempt, "receipt.json")
    if not os.path.isfile(receipt):
        continue
    states = json.loads(io.open(receipt, encoding="utf-8").read())["states"]
    recorded = {os.path.dirname(json.loads(io.open(s, encoding="utf-8")
                                           .read())["scriptPath"])
                for s in states}
    assert len(recorded) == 1, (attempt, sorted(recorded))
    logical = recorded.pop()
    scripts = os.path.join(attempt, "scripts")
    row = {"logical": logical, "source": scripts,
           "sha": boundary.source_sha(scripts), "mode": "ro"}
    if logical in seen:                      # the live binding already has it
        assert seen[logical] == row, (seen[logical], row)
        continue
    out.append(row)
    edits.append(("recorded launch path", logical))

bad = boundary.validate(out)
assert not bad, bad

text = "".join("\t".join(r[k] for k in ("logical", "source", "sha", "mode")) + "\n"
               for r in out)
with io.open(OUT, "x", encoding="utf-8") as fh:
    fh.write(text)
print(OUT)
for kind, logical in edits:
    print("  %-20s %s" % (kind, logical))
