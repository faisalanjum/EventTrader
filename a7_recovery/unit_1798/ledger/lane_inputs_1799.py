# -*- coding: utf-8 -*-
"""The per-lane input declaration for the NEXT root (Codex SEQ 1799).

Completed lanes keep the profile they were proved under; every lane that has
never started gets the SAME exact child payload the running process is measured
to project into a tool-stripped grader child. Membership comes from the frozen
finalized receipts, never from a count or a cutoff.
"""
import collections, hashlib, io, json, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
PUB = R + "/unit_1792/out/candidate_run_1794"
U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = U + "/evidence/lane_input_profiles_1799.json"
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

root = json.load(io.open(PUB + "/root.json", encoding="utf-8"))
called, receipts = set(), []
for name in sorted(os.listdir(PUB)):
    if not (name.startswith("receipt.seg") and name.endswith(".json")):
        continue
    seg = name[len("receipt.seg"):-len(".json")]
    if not os.path.isfile(PUB + "/finalization.seg%s.json" % seg):
        continue                       # only FINALIZED segments count as called
    r = json.load(io.open(PUB + "/" + name, encoding="utf-8"))
    receipts.append({"segment": seg, "rows": len(r["rows"]), "sha256": sha(PUB + "/" + name)})
    called |= {x["lane_id"] for x in r["rows"]}

child = None
for row in root["rows"]:
    if row["lane_id"] in called and row.get("expected_input") is not None:
        child = row["expected_input"]
        break
if child is None:
    print("REFUSED: no completed lane carries a declared child input to reuse")
    sys.exit(1)

profiles = collections.OrderedDict()
for row in root["rows"]:
    profiles[row["lane_id"]] = (row.get("expected_input") if row["lane_id"] in called
                                else collections.OrderedDict(child))
none_lanes = [k for k, v in profiles.items() if v is None]
pending = [r["lane_id"] for r in root["rows"] if r["lane_id"] not in called]
doc = collections.OrderedDict([
    ("purpose", "the input every lane must carry under the next root: completed lanes keep the "
                "profile they were proved under, and every never-started lane declares the exact "
                "child payload the running process projects into a tool-stripped grader"),
    ("source_root", collections.OrderedDict([
        ("path", PUB + "/root.json"), ("sha256", sha(PUB + "/root.json")),
        ("rows", len(root["rows"]))])),
    ("finalized_receipts", receipts),
    ("membership_rule", "a lane is completed iff it appears in a FINALIZED segment receipt; "
                        "nothing is decided by ordinal, count or cached flag"),
    ("child_input_reused_from_the_completed_lanes", child),
    ("counts", collections.OrderedDict([
        ("lanes", len(profiles)), ("completed", len(called)),
        ("never_started", len(pending)),
        ("declare_no_added_input", len(none_lanes)),
        ("declare_the_child_input", len(profiles) - len(none_lanes))])),
    ("pending_first", pending[0] if pending else None),
    ("pending_last", pending[-1] if pending else None),
    ("profiles", profiles)])
io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, indent=1) + "\n")
c = doc["counts"]
print("  lanes %d = completed %d + never started %d" % (c["lanes"], c["completed"], c["never_started"]))
print("  declare NO added input : %d" % c["declare_no_added_input"])
print("  declare the child input: %d" % c["declare_the_child_input"])
print("  pending range          : %s .. %s" % (doc["pending_first"], doc["pending_last"]))
print("  child payload          : %s" % child["payload_sha256"])
print("  -> %s  %s" % (OUT, sha(OUT)[:16]))
